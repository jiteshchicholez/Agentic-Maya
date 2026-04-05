from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from myna.enums import PolicyAction, PolicyScope
from myna.schemas import PolicyDefinition


def _resolve_var(context: dict[str, Any], path: str) -> Any:
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def evaluate_jsonlogic(expression: Any, context: dict[str, Any]) -> Any:
    if not isinstance(expression, dict):
        return expression
    if "var" in expression:
        return _resolve_var(context, expression["var"])
    if len(expression) != 1:
        raise ValueError("jsonlogic expressions must have exactly one operator")
    operator, raw_values = next(iter(expression.items()))
    values = raw_values if isinstance(raw_values, list) else [raw_values]
    resolved = [evaluate_jsonlogic(value, context) for value in values]
    if any(value is None for value in resolved) and operator in {">", ">=", "<", "<=", "in", "contains"}:
        return False
    match operator:
        case "==":
            return resolved[0] == resolved[1]
        case "!=":
            return resolved[0] != resolved[1]
        case ">":
            return resolved[0] > resolved[1]
        case ">=":
            return resolved[0] >= resolved[1]
        case "<":
            return resolved[0] < resolved[1]
        case "<=":
            return resolved[0] <= resolved[1]
        case "and":
            return all(resolved)
        case "or":
            return any(resolved)
        case "not":
            return not resolved[0]
        case "in":
            return resolved[0] in resolved[1]
        case "contains":
            return resolved[1] in resolved[0]
        case _:
            raise ValueError(f"unsupported jsonlogic operator: {operator}")


@dataclass(slots=True)
class PolicyDecision:
    action: PolicyAction
    messages: list[str]
    matched_policies: list[str]
    notify_human: bool


def builtin_policies() -> list[PolicyDefinition]:
    return [
        PolicyDefinition(
            id="policy.no_external_without_permission",
            name="No external calls without permission",
            scope=PolicyScope.AGENT,
            trigger={
                "and": [
                    {"==": [{"var": "action_type"}, "external_call"]},
                    {"==": [{"var": "external_calls"}, False]},
                ]
            },
            action=PolicyAction.DENY,
            message="External calls require explicit permission.",
            log_level="ERROR",
            notify_human=True,
        ),
        PolicyDefinition(
            id="policy.budget_ceiling_enforcement",
            name="Budget ceiling enforcement",
            scope=PolicyScope.AGENT,
            trigger={
                "or": [
                    {">": [{"var": "budget.projected_tokens"}, {"var": "budget.max_tokens"}]},
                    {">": [{"var": "budget.projected_cost"}, {"var": "budget.max_cost"}]},
                    {">": [{"var": "budget.projected_tool_calls"}, {"var": "budget.max_tool_calls"}]},
                    {">": [{"var": "tokens_used"}, {"var": "max_tokens"}]},
                    {">": [{"var": "cost_usd_used"}, {"var": "max_cost_usd"}]},
                    {">": [{"var": "tool_calls_used"}, {"var": "max_tool_calls"}]},
                ]
            },
            action=PolicyAction.HALT,
            message="Budget ceiling exceeded.",
            log_level="CRITICAL",
            notify_human=True,
        ),
        PolicyDefinition(
            id="policy.critic_required_for_high_risk",
            name="Critic required for high risk",
            scope=PolicyScope.PIPELINE,
            trigger={
                "and": [
                    {">=": [{"var": "action.risk_rank"}, 3]},
                    {"==": [{"var": "action.requires_critic"}, False]},
                ]
            },
            action=PolicyAction.WARN,
            message="High-risk actions should invoke a critic review.",
            log_level="WARN",
            notify_human=False,
        ),
        PolicyDefinition(
            id="policy.audit_all_memory_writes",
            name="Audit all memory writes",
            scope=PolicyScope.AGENT,
            trigger={"==": [{"var": "action.type"}, "memory_write"]},
            action=PolicyAction.ALLOW,
            message="Memory writes are auditable actions.",
            log_level="INFO",
            notify_human=False,
        ),
        PolicyDefinition(
            id="policy.human_approval_before_critical",
            name="Human approval before critical",
            scope=PolicyScope.PIPELINE,
            trigger={"==": [{"var": "action.risk_level"}, "CRITICAL"]},
            action=PolicyAction.ESCALATE,
            message="Critical actions require typed confirmation.",
            log_level="CRITICAL",
            notify_human=True,
        ),
        PolicyDefinition(
            id="policy.no_agent_reads_sibling_memory",
            name="No sibling memory reads",
            scope=PolicyScope.AGENT,
            trigger={
                "and": [
                    {"==": [{"var": "action.type"}, "memory_read"]},
                    {"!=": [{"var": "action.target_agent"}, {"var": "agent.id"}]},
                    {"!=": [{"var": "action.target_agent"}, None]},
                ]
            },
            action=PolicyAction.DENY,
            message="Agents may not read sibling memory directly.",
            log_level="ERROR",
            notify_human=False,
        ),
        PolicyDefinition(
            id="policy.max_subagent_depth_3",
            name="Maximum subagent depth 3",
            scope=PolicyScope.AGENT,
            trigger={">": [{"var": "agent.spawn_depth"}, 3]},
            action=PolicyAction.DENY,
            message="Subagent depth exceeds the allowed limit.",
            log_level="ERROR",
            notify_human=True,
        ),
    ]


class PolicyEngine:
    ACTION_ORDER = {
        PolicyAction.ALLOW: 0,
        PolicyAction.WARN: 1,
        PolicyAction.ESCALATE: 2,
        PolicyAction.DENY: 3,
        PolicyAction.HALT: 4,
        PolicyAction.ROLLBACK: 5,
    }

    def __init__(self, policies: list[PolicyDefinition] | None = None):
        self._policies = {policy.id: policy for policy in policies or []}

    def register(self, policy: PolicyDefinition) -> None:
        self._policies[policy.id] = policy

    def list(self) -> list[PolicyDefinition]:
        return list(self._policies.values())

    def load_builtin_policies(self) -> None:
        for policy in builtin_policies():
            self.register(policy)

    def evaluate(self, context: dict[str, Any] | None = None, scope: PolicyScope | None = None, policy_id: str | None = None) -> PolicyDecision:
        context = context or {}
        matched: list[PolicyDefinition] = []
        policies = [self._policies[policy_id]] if policy_id is not None else self._policies.values()
        for policy in policies:
            if not policy.enabled:
                continue
            if scope and policy.scope not in {scope, PolicyScope.GLOBAL}:
                continue
            if evaluate_jsonlogic(policy.trigger, context):
                matched.append(policy)
        if not matched:
            return PolicyDecision(PolicyAction.ALLOW, [], [], False)
        final = max(matched, key=lambda policy: self.ACTION_ORDER[policy.action]).action
        return PolicyDecision(
            action=final,
            messages=[policy.message for policy in matched],
            matched_policies=[policy.id for policy in matched],
            notify_human=any(policy.notify_human for policy in matched),
        )

    def evaluate_all(self, context: dict[str, Any], scope: PolicyScope | None = None) -> PolicyDecision:
        return self.evaluate(context=context, scope=scope)

    def override(self, policy_id: str, override_action: PolicyAction, approved_by: str | None = None) -> None:
        if policy_id not in self._policies:
            raise KeyError(f"policy '{policy_id}' not found")
        if approved_by is None:
            raise PermissionError("human approval required to override policy")
        self._policies[policy_id].action = override_action
