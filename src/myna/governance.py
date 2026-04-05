from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Any

from myna.enums import MemoryAccess, MemoryTier, PolicyAction, PolicyScope, RiskLevel
from myna.policy import PolicyDecision, PolicyEngine
from myna.schemas import BudgetBlock, GlobalBudgetBlock, PermissionsBlock, SpawnAgentBlock
from myna.utils import safe_relative_to


RISK_RANK = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


@dataclass(slots=True)
class ActionRequest:
    type: str
    summary: str
    risk_level: RiskLevel
    tool_name: str | None = None
    file_path: str | None = None
    memory_tier: MemoryTier | None = None
    memory_mode: str | None = None
    target_agent: str | None = None
    external_call: bool = False
    requires_critic: bool = False
    stateful: bool = False
    estimated_tokens: int = 0
    estimated_cost: float = 0.0
    tool_calls: int = 0
    spawn_depth: int = 0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GovernanceResult:
    allowed: bool
    layers: dict[str, str]
    approval_required: bool = False
    typed_confirmation_required: bool = False
    checkpoint_required: bool = False
    halt_reason: str | None = None
    budget_exceeded: bool = False
    policy_decision: PolicyDecision | None = None


@dataclass(slots=True)
class CheckResult:
    allowed: bool
    reason: str


@dataclass(slots=True)
class RiskCheckResult:
    allowed: bool
    requires_hitl: bool
    requires_typed_confirmation: bool


class IntentVerifier:
    INTERNAL_PREFIXES = ("internal:", "checkpoint", "rollback", "audit", "status")

    @classmethod
    def _stem(cls, word: str) -> str:
        """Simple stemming: remove common suffixes."""
        word = word.lower()
        suffixes = ['ize', 'ing', 'ed', 's', 'ly', 'er', 'est', 'al', 'y']
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 1:
                return word[:-len(suffix)]
        return word

    @classmethod
    def verify(cls, root_intent: str, current_task: str, action_summary: str) -> tuple[bool, str]:
        summary = action_summary.lower().strip()
        if any(summary.startswith(prefix) for prefix in cls.INTERNAL_PREFIXES):
            return True, "internal action"
        root_terms = {cls._stem(term) for term in root_intent.lower().split() if len(term) > 2}
        task_terms = {cls._stem(term) for term in current_task.lower().split() if len(term) > 2}
        summary_terms = {cls._stem(term) for term in summary.split() if len(term) > 2}
        overlap = summary_terms & (root_terms | task_terms)
        if overlap:
            return True, f"matched intent terms: {', '.join(sorted(overlap))}"
        return False, "no overlap with root intent or current task"


class BudgetTracker:
    def __init__(self, global_budget):
        self.global_budget = global_budget
        self.pipeline_tokens = 0
        self.pipeline_cost = 0.0
        self.pipeline_tool_calls = 0
        self.pipeline_started = monotonic()
        self._agent_budgets: dict[str, BudgetBlock] = {}
        self._agent_counters: dict[str, dict[str, float]] = {}
        self._agent_started: dict[str, float] = {}

    def register_agent(self, agent: SpawnAgentBlock) -> None:
        self._agent_budgets[agent.id] = agent.budget
        self._agent_counters[agent.id] = {"tokens": 0, "cost": 0.0, "tool_calls": 0}
        self._agent_started[agent.id] = monotonic()

    def projected(self, agent_id: str, request: ActionRequest) -> dict[str, float]:
        counters = self._agent_counters[agent_id]
        budget = self._agent_budgets[agent_id]
        elapsed = monotonic() - self._agent_started[agent_id]
        return {
            "projected_tokens": counters["tokens"] + request.estimated_tokens,
            "projected_cost": counters["cost"] + request.estimated_cost,
            "projected_tool_calls": counters["tool_calls"] + request.tool_calls,
            "max_tokens": budget.max_tokens_per_agent,
            "max_cost": budget.max_cost_usd,
            "max_tool_calls": budget.max_tool_calls,
            "elapsed": elapsed,
            "max_wall_time": budget.max_wall_time_sec,
        }

    def check(self, agent_id: str, request: ActionRequest) -> tuple[bool, str]:
        projection = self.projected(agent_id, request)
        if projection["projected_tokens"] > projection["max_tokens"]:
            return False, "max_tokens_per_agent exceeded"
        if projection["projected_cost"] > projection["max_cost"]:
            return False, "max_cost_usd exceeded"
        if projection["projected_tool_calls"] > projection["max_tool_calls"]:
            return False, "max_tool_calls exceeded"
        if projection["elapsed"] > projection["max_wall_time"]:
            return False, "max_wall_time_sec exceeded"
        if self.pipeline_tokens + request.estimated_tokens > self.global_budget.max_total_tokens:
            return False, "max_total_tokens exceeded"
        if self.pipeline_cost + request.estimated_cost > self.global_budget.max_total_cost_usd:
            return False, "max_total_cost_usd exceeded"
        if monotonic() - self.pipeline_started > self.global_budget.max_total_time_sec:
            return False, "max_total_time_sec exceeded"
        return True, "within budget"

    def consume(self, agent_id: str, request: ActionRequest) -> None:
        self._agent_counters[agent_id]["tokens"] += request.estimated_tokens
        self._agent_counters[agent_id]["cost"] += request.estimated_cost
        self._agent_counters[agent_id]["tool_calls"] += request.tool_calls
        self.pipeline_tokens += request.estimated_tokens
        self.pipeline_cost += request.estimated_cost
        self.pipeline_tool_calls += request.tool_calls


class PermissionGuard:
    @staticmethod
    def check_memory(permissions: PermissionsBlock, mode: str) -> tuple[bool, str]:
        if mode == "read" and permissions.memory in {MemoryAccess.READ, MemoryAccess.WRITE}:
            return True, "memory read allowed"
        if mode == "write" and permissions.memory == MemoryAccess.WRITE:
            return True, "memory write allowed"
        return False, f"memory permission '{permissions.memory}' does not allow {mode}"

    @staticmethod
    def check_tool(permissions: PermissionsBlock, tool_name: str) -> tuple[bool, str]:
        if tool_name in permissions.tools:
            return True, "tool allowed"
        return False, f"tool '{tool_name}' is outside the permission scope"

    @staticmethod
    def check_spawn(permissions: PermissionsBlock) -> tuple[bool, str]:
        if permissions.spawn_agents:
            return True, "subagent spawn allowed"
        return False, "spawn_agents is disabled"

    @staticmethod
    def check_file(permissions: PermissionsBlock, file_path: Path, sandbox_root: Path) -> tuple[bool, str]:
        for allowed in permissions.file_access:
            candidate_root = sandbox_root / allowed
            if safe_relative_to(file_path, candidate_root):
                return True, f"file path allowed under {candidate_root}"
        return False, "file path is outside the permitted namespace"


class GovernanceEngine:
    def __init__(self, policy_engine: PolicyEngine, budget_tracker: BudgetTracker | None = None, sandbox_root: Path | None = None):
        self.policy_engine = policy_engine
        self.budget_tracker = budget_tracker or BudgetTracker(GlobalBudgetBlock())
        self.sandbox_root = sandbox_root or Path.cwd()

    def check_intent(self, declared_intent: str, proposed_action: str, agent_id: str) -> CheckResult:
        allowed, reason = IntentVerifier.verify(declared_intent, "", proposed_action)
        if allowed:
            return CheckResult(True, "intent matched")
        return CheckResult(False, reason)

    def check_tool_permission(
        self,
        agent_id: str,
        tool_id: str,
        permissions: PermissionsBlock,
        audit_logger: Any | None = None,
    ) -> CheckResult:
        allowed, reason = PermissionGuard.check_tool(permissions, tool_id)
        if audit_logger is not None:
            audit_logger.append_entry(
                agent_id=agent_id,
                role="governance",
                action_type="tool_permission",
                governance_layer="L2",
                outcome="allowed" if allowed else "denied",
                input_payload={"tool_id": tool_id},
                output_payload={"allowed": allowed},
            )
        return CheckResult(allowed, reason)

    def check_external_call(self, agent_id: str, permissions: PermissionsBlock, url: str) -> CheckResult:
        if permissions.external_calls:
            return CheckResult(True, "external call permitted")
        return CheckResult(False, "external calls are disabled")

    def check_budget(
        self,
        agent_id: str,
        budget: BudgetBlock,
        tokens_used: int,
        tool_calls_used: int,
        cost_usd_used: float,
        wall_time_sec: int,
    ) -> CheckResult:
        if tokens_used > budget.max_tokens_per_agent:
            return CheckResult(False, "max_tokens_per_agent exceeded")
        if tool_calls_used > budget.max_tool_calls:
            return CheckResult(False, "max_tool_calls exceeded")
        if cost_usd_used > budget.max_cost_usd:
            return CheckResult(False, "max_cost_usd exceeded")
        if wall_time_sec > budget.max_wall_time_sec:
            return CheckResult(False, "max_wall_time_sec exceeded")
        return CheckResult(True, "within budget")

    def check_file_access(
        self,
        agent_id: str,
        requested_path: str,
        permissions: PermissionsBlock,
        workspace_root: Path,
    ) -> CheckResult:
        file_path = Path(requested_path)
        if not file_path.is_absolute():
            file_path = workspace_root / file_path
        allowed, reason = PermissionGuard.check_file(permissions, file_path, workspace_root / agent_id)
        return CheckResult(allowed, reason)

    def check_memory_access(
        self,
        requesting_agent_id: str,
        target_agent_id: str,
        operation: str,
    ) -> CheckResult:
        if requesting_agent_id == target_agent_id:
            return CheckResult(True, "same agent memory access")
        if operation.lower() in {"read", "write"}:
            return CheckResult(False, "cannot access sibling memory")
        return CheckResult(True, "memory operation permitted")

    def check_risk_level(self, agent_id: str, risk_level: RiskLevel, action_description: str) -> RiskCheckResult:
        if risk_level == RiskLevel.CRITICAL:
            return RiskCheckResult(False, True, True)
        if risk_level == RiskLevel.HIGH:
            return RiskCheckResult(False, True, False)
        return RiskCheckResult(True, False, False)

    def check_spawn_permission(self, agent_id: str, permissions: PermissionsBlock) -> CheckResult:
        allowed, reason = PermissionGuard.check_spawn(permissions)
        return CheckResult(allowed, reason)

    def check_skill_enabled(self, skill_id: str, skill_registry: Any) -> CheckResult:
        try:
            skill = skill_registry.get(skill_id)
        except Exception:
            return CheckResult(False, "skill not registered")
        if getattr(skill, "enabled", False):
            return CheckResult(True, "skill enabled")
        return CheckResult(False, "skill is disabled")

    def evaluate_action(
        self,
        *,
        agent: SpawnAgentBlock,
        request: ActionRequest,
        root_intent: str,
        current_task: str,
    ) -> GovernanceResult:
        layers: dict[str, str] = {}

        intent_ok, intent_reason = IntentVerifier.verify(root_intent, current_task, request.summary)
        layers["L1"] = intent_reason
        if not intent_ok:
            return GovernanceResult(False, layers, halt_reason="intent mismatch")

        permission_ok, permission_reason = self._check_permissions(agent, request)
        layers["L2"] = permission_reason
        if not permission_ok:
            return GovernanceResult(False, layers, halt_reason="permission denied")

        budget_ok, budget_reason = self.budget_tracker.check(agent.id, request)
        layers["L3"] = budget_reason
        if not budget_ok:
            return GovernanceResult(False, layers, halt_reason=budget_reason, budget_exceeded=True)

        sandbox_ok, sandbox_reason = self._check_sandbox(agent, request)
        layers["L4"] = sandbox_reason
        if not sandbox_ok:
            return GovernanceResult(False, layers, halt_reason="sandbox violation")

        policy_context = {
            "agent": {"id": agent.id, "spawn_depth": request.spawn_depth},
            "action": {
                "type": request.type,
                "risk_level": request.risk_level,
                "risk_rank": RISK_RANK[request.risk_level],
                "requires_critic": request.requires_critic,
                "external_call": request.external_call,
                "target_agent": request.target_agent,
            },
            "permissions": agent.permissions.model_dump(mode="python"),
            "budget": self.budget_tracker.projected(agent.id, request),
        }
        policy_decision = self.policy_engine.evaluate(policy_context, PolicyScope.AGENT)
        layers["POLICY"] = ", ".join(policy_decision.messages) if policy_decision.messages else "no policy flags"
        if policy_decision.action in {PolicyAction.DENY, PolicyAction.HALT, PolicyAction.ROLLBACK}:
            return GovernanceResult(False, layers, halt_reason="; ".join(policy_decision.messages), policy_decision=policy_decision)

        approval_required = request.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL} or policy_decision.action == PolicyAction.ESCALATE
        typed_confirmation_required = request.risk_level == RiskLevel.CRITICAL
        layers["L5"] = "human approval required" if approval_required else "auto-approved"
        layers["L6"] = "audit entry required"

        return GovernanceResult(
            True,
            layers,
            approval_required=approval_required,
            typed_confirmation_required=typed_confirmation_required,
            checkpoint_required=request.stateful,
            policy_decision=policy_decision,
        )

    def record_consumption(self, agent_id: str, request: ActionRequest) -> None:
        self.budget_tracker.consume(agent_id, request)

    def _check_permissions(self, agent: SpawnAgentBlock, request: ActionRequest) -> tuple[bool, str]:
        if request.type in {"tool", "critic_review"} and request.tool_name:
            return PermissionGuard.check_tool(agent.permissions, request.tool_name)
        if request.type == "memory_read":
            return PermissionGuard.check_memory(agent.permissions, "read")
        if request.type == "memory_write":
            return PermissionGuard.check_memory(agent.permissions, "write")
        if request.type == "spawn_agent":
            return PermissionGuard.check_spawn(agent.permissions)
        if request.external_call and not agent.permissions.external_calls:
            return False, "external calls are disabled"
        return True, "permissions satisfied"

    def _check_sandbox(self, agent: SpawnAgentBlock, request: ActionRequest) -> tuple[bool, str]:
        if request.file_path:
            file_path = Path(request.file_path)
            if not file_path.is_absolute():
                file_path = self.sandbox_root / agent.id / request.file_path
            return PermissionGuard.check_file(agent.permissions, file_path, self.sandbox_root / agent.id)
        if request.external_call and not agent.permissions.external_calls:
            return False, "external network calls are not permitted"
        return True, "sandbox constraints satisfied"
