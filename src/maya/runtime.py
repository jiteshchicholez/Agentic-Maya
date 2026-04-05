from __future__ import annotations

import json
import multiprocessing as mp
import shlex
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from queue import Empty
from typing import Any

from maya.audit import AuditClient, AuditLog, audit_worker_main
from maya.config import AppConfig
from maya.enums import AgentRole, AgentStatus, MemoryTier, PipelineStatus, RiskLevel
from maya.governance import ActionRequest, BudgetTracker, GovernanceEngine
from maya.loader import load_directory_models, load_policy
from maya.memory import MemoryManager
from maya.model_client import CompletionResult, OpenAICompatibleModelClient
from maya.persistence import PersistenceStore
from maya.policy import PolicyEngine, builtin_policies
from maya.schemas import ApprovalRequest, CheckpointRecord, MessageEnvelope, PipelineDefinition, PipelineStep, SpawnAgentBlock
from maya.skills import SkillRegistry
from maya.utils import ensure_dir, safe_relative_to


class LocalAuditClient:
    def __init__(self, audit_log: AuditLog):
        self.audit_log = audit_log

    def append(self, **payload) -> dict[str, Any]:
        entry = self.audit_log.append_entry(**payload)
        return entry.model_dump(mode="json")

    def entries(self) -> list[dict[str, Any]]:
        return self.audit_log.entries()

    def close(self) -> None:
        return None


def generic_agent_worker(agent_payload: dict[str, Any], inbound_queue, outbound_queue) -> None:
    agent_id = agent_payload["id"]
    outbound_queue.put({"kind": "agent_started", "agent_id": agent_id, "role": agent_payload["role"]})
    while True:
        command = inbound_queue.get()
        kind = command.get("kind")
        if kind == "terminate":
            outbound_queue.put({"kind": "agent_stopped", "agent_id": agent_id})
            return
        if kind == "run_step":
            step = command["step"]
            action_input = command.get("resolved_action_input", step.get("action_input", {}))
            outbound_queue.put(
                {
                    "kind": "action_request",
                    "agent_id": agent_id,
                    "role": agent_payload["role"],
                    "step": step["step"],
                    "task": step["task"],
                    "action_type": step["action_type"],
                    "risk_level": step["risk_level"],
                    "requires_critic": step.get("requires_critic", False),
                    "action_input": action_input,
                    "output_memory_tier": step.get("output_memory_tier"),
                }
            )
            response = inbound_queue.get()
            outbound_queue.put(
                {
                    "kind": "step_result",
                    "agent_id": agent_id,
                    "step": step["step"],
                    "status": response["status"],
                    "result": response.get("result"),
                    "error": response.get("error"),
                }
            )


def tool_executor_main(request_queue, response_queue, session_root: str) -> None:
    root = Path(session_root)
    while True:
        request = request_queue.get()
        kind = request.get("kind")
        if kind == "close":
            response_queue.put({"kind": "closed"})
            return
        if kind != "execute":
            response_queue.put({"kind": "error", "error": f"unsupported request: {kind}"})
            continue

        tool_name = request["tool_name"]
        workdir = Path(request["workdir"])
        agent_root = Path(request.get("agent_root", workdir))
        path = Path(request.get("path", workdir))
        if not path.is_absolute():
            path = agent_root / path
        if not safe_relative_to(path, root):
            response_queue.put({"kind": "error", "error": "path escapes tool sandbox"})
            continue

        try:
            if tool_name == "file_read":
                response_queue.put({"kind": "result", "result": {"content": path.read_text(encoding="utf-8"), "path": str(path)}})
            elif tool_name == "file_write":
                ensure_dir(path.parent)
                path.write_text(request["content"], encoding="utf-8")
                response_queue.put({"kind": "result", "result": {"path": str(path)}})
            elif tool_name == "code_exec":
                command = request["command"]
                shell = isinstance(command, str)
                completed = subprocess.run(
                    command if shell else list(command),
                    cwd=workdir,
                    capture_output=True,
                    text=True,
                    timeout=request.get("timeout", 30),
                    shell=shell,
                )
                response_queue.put(
                    {
                        "kind": "result",
                        "result": {
                            "stdout": completed.stdout,
                            "stderr": completed.stderr,
                            "returncode": completed.returncode,
                        },
                    }
                )
            else:
                response_queue.put({"kind": "error", "error": f"unsupported tool: {tool_name}"})
        except Exception as exc:
            response_queue.put({"kind": "error", "error": str(exc)})


@dataclass(slots=True)
class RuntimeReport:
    session_id: str
    status: str
    step_outputs: dict[int, Any]


class CheckpointManager:
    def __init__(self, session_dir: Path, store: PersistenceStore):
        self.session_dir = session_dir
        self.store = store
        self.checkpoints_dir = ensure_dir(session_dir / "checkpoints")
        self.db_path = session_dir / "state.sqlite3"
        self.agents_dir = ensure_dir(session_dir / "agents")

    def create(self, session_id: str, reason: str, pipeline_state: dict[str, Any]) -> CheckpointRecord:
        checkpoint_dir = ensure_dir(self.checkpoints_dir / str(uuid.uuid4()))
        db_snapshot_path = checkpoint_dir / "state.sqlite3"
        if self.db_path.exists():
            shutil.copy2(self.db_path, db_snapshot_path)
        workdir_snapshot_path = checkpoint_dir / "agents"
        if self.agents_dir.exists():
            shutil.copytree(self.agents_dir, workdir_snapshot_path, dirs_exist_ok=True)
        record = CheckpointRecord(
            session_id=session_id,
            reason=reason,
            db_snapshot_path=str(db_snapshot_path),
            workdir_snapshot_path=str(workdir_snapshot_path),
            pipeline_state=pipeline_state,
        )
        self.store.create_checkpoint(record)
        return record

    def rollback(self, checkpoint_id: str) -> dict[str, Any]:
        checkpoint = self.store.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"checkpoint '{checkpoint_id}' does not exist")
        db_snapshot_path = Path(checkpoint["db_snapshot_path"])
        if db_snapshot_path.exists():
            shutil.copy2(db_snapshot_path, self.db_path)
        workdir_snapshot = Path(checkpoint["workdir_snapshot_path"])
        if workdir_snapshot.exists():
            if self.agents_dir.exists():
                shutil.rmtree(self.agents_dir)
            shutil.copytree(workdir_snapshot, self.agents_dir, dirs_exist_ok=True)
        return checkpoint


class SessionRuntime:
    def __init__(
        self,
        *,
        project_root: Path,
        config: AppConfig,
        model_client=None,
        session_id: str | None = None,
    ):
        self.project_root = project_root
        self.config = config
        self.session_id = session_id or str(uuid.uuid4())
        self.session_root = config.session_root_path(project_root)
        self.session_dir = ensure_dir(self.session_root / self.session_id)
        self.agents_dir = ensure_dir(self.session_dir / "agents")
        self.db_path = self.session_dir / "state.sqlite3"
        self.store = PersistenceStore(self.db_path)
        self.audit_log = AuditLog(self.session_dir / "audit.jsonl")
        self.policy_engine = PolicyEngine(builtin_policies())
        self.skill_registry = SkillRegistry(self.store)
        self.model_client = model_client or OpenAICompatibleModelClient(config.provider.api_key)
        self.memory_manager = MemoryManager(
            store=self.store,
            session_id=self.session_id,
            model_client=self.model_client,
            embedding_model=config.provider.embedding_model,
            base_url=config.provider.base_url,
        )
        self.checkpoint_manager = CheckpointManager(self.session_dir, self.store)
        self._ctx = mp.get_context("spawn")
        self._audit_process = None
        self._audit_client: AuditClient | None = None
        self._tool_process = None
        self._tool_request_queue = None
        self._tool_response_queue = None
        self._agent_processes: dict[str, mp.Process] = {}
        self._agent_inbound_queues: dict[str, Any] = {}
        self._event_queue = None
        self._agents: dict[str, SpawnAgentBlock] = {}
        self._budget_tracker: BudgetTracker | None = None
        self._governance: GovernanceEngine | None = None
        self._pipeline: PipelineDefinition | None = None
        self._use_processes = True

    @property
    def governance(self) -> GovernanceEngine:
        if self._governance is None:
            raise RuntimeError("runtime not initialized")
        return self._governance

    @property
    def budget_tracker(self) -> BudgetTracker:
        if self._budget_tracker is None:
            raise RuntimeError("runtime not initialized")
        return self._budget_tracker

    @property
    def audit_client(self) -> AuditClient:
        if self._audit_client is None:
            raise RuntimeError("runtime not initialized")
        return self._audit_client

    def initialize(self, pipeline: PipelineDefinition) -> None:
        self._pipeline = pipeline
        self.skill_registry.seed_builtin_skills()
        self.skill_registry.load_directory(self.project_root / self.config.paths.skill_dir)

        for policy in load_directory_models(self.project_root / self.config.paths.policy_dir, load_policy):
            self.policy_engine.register(policy)
            self.store.upsert_policy(policy, str(self.project_root / self.config.paths.policy_dir))
        for policy in self.policy_engine.list():
            self.store.upsert_policy(policy, "builtin")

        self.store.create_session(self.session_id, pipeline.id, pipeline.root_intent, PipelineStatus.CREATED)
        self._budget_tracker = BudgetTracker(pipeline.global_budget)
        self._governance = GovernanceEngine(self.policy_engine, self._budget_tracker, self.agents_dir)
        self._start_services()

        for agent in pipeline.agents:
            self._agents[agent.id] = agent
            ensure_dir(self.agents_dir / agent.id / "workspace")
            self.store.record_agent(self.session_id, agent, AgentStatus.IDLE)
            self.budget_tracker.register_agent(agent)

        self.store.update_agent_status(self.session_id, pipeline.orchestrator, AgentStatus.RUNNING)
        self._spawn_worker_agents()
        self._audit(
            agent_id=pipeline.orchestrator,
            role=AgentRole.ORCHESTRATOR,
            action_type="pipeline_initialize",
            governance_layer="L1-L7",
            outcome="success",
            input_payload={"pipeline_id": pipeline.id},
            output_payload={"session_id": self.session_id},
        )

    def _start_services(self) -> None:
        try:
            self._event_queue = self._ctx.Queue()
            audit_request_queue = self._ctx.Queue()
            audit_response_queue = self._ctx.Queue()
            self._audit_process = self._ctx.Process(
                target=audit_worker_main,
                args=(audit_request_queue, audit_response_queue, str(self.session_dir / "audit.jsonl")),
                name=f"maya-audit-{self.session_id}",
            )
            self._audit_process.start()
            self._audit_client = AuditClient(audit_request_queue, audit_response_queue)

            self._tool_request_queue = self._ctx.Queue()
            self._tool_response_queue = self._ctx.Queue()
            self._tool_process = self._ctx.Process(
                target=tool_executor_main,
                args=(self._tool_request_queue, self._tool_response_queue, str(self.session_dir)),
                name=f"maya-tool-{self.session_id}",
            )
            self._tool_process.start()
        except PermissionError:
            self._use_processes = False
            self._event_queue = None
            self._audit_client = LocalAuditClient(self.audit_log)
            self._tool_request_queue = None
            self._tool_response_queue = None
            self._tool_process = None

    def _spawn_worker_agents(self) -> None:
        assert self._pipeline is not None
        for agent in self._pipeline.agents:
            if agent.role in {AgentRole.ORCHESTRATOR, AgentRole.AUDIT_AGENT, AgentRole.TOOL_EXEC}:
                if agent.role != AgentRole.ORCHESTRATOR:
                    self.store.update_agent_status(self.session_id, agent.id, AgentStatus.RUNNING)
                continue
            if not self._use_processes:
                self.store.update_agent_status(self.session_id, agent.id, AgentStatus.RUNNING)
                continue
            inbound = self._ctx.Queue()
            process = self._ctx.Process(
                target=generic_agent_worker,
                args=(agent.model_dump(mode="python"), inbound, self._event_queue),
                name=f"maya-agent-{agent.id}",
            )
            process.start()
            self._agent_inbound_queues[agent.id] = inbound
            self._agent_processes[agent.id] = process
            self.store.update_agent_status(self.session_id, agent.id, AgentStatus.RUNNING)

    def _audit(
        self,
        *,
        agent_id: str,
        role: str | AgentRole,
        action_type: str,
        governance_layer: str,
        outcome: str,
        input_payload: Any,
        output_payload: Any,
        tool_used: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.audit_client.append(
            agent_id=agent_id,
            role=str(role),
            action_type=action_type,
            governance_layer=governance_layer,
            outcome=outcome,
            input_payload=input_payload,
            output_payload=output_payload,
            tool_used=tool_used,
            details=details or {},
        )

    def _resolve_references(self, value: Any, step_outputs: dict[int, Any]) -> Any:
        if isinstance(value, dict):
            return {key: self._resolve_references(item, step_outputs) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_references(item, step_outputs) for item in value]
        if isinstance(value, str) and value.startswith("{{step:") and value.endswith("}}"):
            inner = value[7:-2]
            step_id_text, *path_parts = inner.split(".")
            payload = step_outputs[int(step_id_text)]
            for part in path_parts:
                if isinstance(payload, dict):
                    payload = payload.get(part)
                else:
                    payload = None
            return payload
        return value

    def status_snapshot(self) -> dict[str, Any]:
        return {
            "session": self.store.get_session(self.session_id),
            "agents": self.store.list_agents(self.session_id),
            "approvals": self.store.list_approvals(self.session_id),
            "checkpoints": self.store.list_checkpoints(self.session_id),
        }

    def audit_entries(self) -> list[dict[str, Any]]:
        return self.audit_log.entries()

    def checkpoint(self, reason: str) -> CheckpointRecord:
        pipeline_state = {"status": self.store.get_session(self.session_id), "agents": self.store.list_agents(self.session_id)}
        record = self.checkpoint_manager.create(self.session_id, reason, pipeline_state)
        self._audit(
            agent_id=self._pipeline.orchestrator if self._pipeline else "system",
            role=AgentRole.ORCHESTRATOR if self._pipeline else "system",
            action_type="checkpoint",
            governance_layer="L7",
            outcome="success",
            input_payload={"reason": reason},
            output_payload=record.model_dump(mode="json"),
        )
        return record

    def rollback(self, checkpoint_id: str) -> dict[str, Any]:
        checkpoint = self.checkpoint_manager.rollback(checkpoint_id)
        self._audit(
            agent_id=self._pipeline.orchestrator if self._pipeline else "system",
            role=AgentRole.ORCHESTRATOR if self._pipeline else "system",
            action_type="rollback",
            governance_layer="L7",
            outcome="success",
            input_payload={"checkpoint_id": checkpoint_id},
            output_payload=checkpoint,
        )
        return checkpoint

    def approve(self, request_id: str, confirmation: str | None = None) -> dict[str, Any]:
        approval = self.store.get_approval(request_id)
        if not approval:
            raise ValueError(f"approval '{request_id}' not found")
        if approval["typed_confirmation_required"] and confirmation != request_id:
            raise ValueError("typed confirmation must match the request id")
        self.store.update_approval(request_id, "approved", "approved by human")
        resolved = self.store.get_approval(request_id)
        self._audit(
            agent_id=approval["agent_id"],
            role=self._agents[approval["agent_id"]].role if approval["agent_id"] in self._agents else "system",
            action_type="approval",
            governance_layer="L5",
            outcome="approved",
            input_payload=approval,
            output_payload=resolved,
        )
        return resolved

    def deny(self, request_id: str, reason: str | None = None) -> dict[str, Any]:
        approval = self.store.get_approval(request_id)
        if not approval:
            raise ValueError(f"approval '{request_id}' not found")
        self.store.update_approval(request_id, "denied", reason or "denied by human")
        resolved = self.store.get_approval(request_id)
        self._audit(
            agent_id=approval["agent_id"],
            role=self._agents[approval["agent_id"]].role if approval["agent_id"] in self._agents else "system",
            action_type="approval",
            governance_layer="L5",
            outcome="denied",
            input_payload=approval,
            output_payload=resolved,
        )
        return resolved

    def pause(self, agent_id: str) -> None:
        self.store.update_agent_status(self.session_id, agent_id, AgentStatus.PAUSED)

    def resume(self, agent_id: str) -> None:
        self.store.update_agent_status(self.session_id, agent_id, AgentStatus.RUNNING)

    def terminate(self, agent_id: str) -> None:
        if agent_id in self._agent_inbound_queues:
            self._agent_inbound_queues[agent_id].put({"kind": "terminate"})
        self.store.update_agent_status(self.session_id, agent_id, AgentStatus.TERMINATED)

    def run_pipeline(self, pipeline: PipelineDefinition, interactive: bool = False) -> RuntimeReport:
        self.initialize(pipeline)
        self.store.update_session_status(self.session_id, PipelineStatus.RUNNING)
        step_outputs: dict[int, Any] = {}
        completed_steps: set[int] = set()
        try:
            for step in sorted(pipeline.flow, key=lambda item: item.step):
                if not set(step.depends_on).issubset(completed_steps):
                    raise RuntimeError(f"step {step.step} dependencies not satisfied")
                result = self._run_step(step, step_outputs, interactive=interactive)
                step_outputs[step.step] = result
                completed_steps.add(step.step)
            self.store.update_session_status(self.session_id, PipelineStatus.SUCCESS)
            self.store.update_agent_status(self.session_id, pipeline.orchestrator, AgentStatus.SUCCESS)
            return RuntimeReport(self.session_id, PipelineStatus.SUCCESS, step_outputs)
        except Exception as exc:
            self.store.update_session_status(self.session_id, PipelineStatus.FAILED)
            self.store.update_agent_status(self.session_id, pipeline.orchestrator, AgentStatus.FAILED)
            self._audit(
                agent_id=pipeline.orchestrator,
                role=AgentRole.ORCHESTRATOR,
                action_type="pipeline_failed",
                governance_layer="L1-L7",
                outcome="failed",
                input_payload={"pipeline_id": pipeline.id},
                output_payload={"error": str(exc)},
            )
            raise
        finally:
            self.shutdown()

    def _run_step(self, step: PipelineStep, step_outputs: dict[int, Any], interactive: bool) -> Any:
        agent = self._agents[step.agent]
        resolved_input = self._resolve_references(step.action_input, step_outputs)
        if not self._use_processes or step.agent not in self._agent_inbound_queues:
            result = self._execute_action(agent, step, resolved_input, interactive)
            self.store.update_agent_status(self.session_id, step.agent, AgentStatus.SUCCESS)
            return result

        self._agent_inbound_queues[step.agent].put(
            {
                "kind": "run_step",
                "step": step.model_dump(mode="python"),
                "resolved_action_input": resolved_input,
            }
        )
        while True:
            event = self._event_queue.get(timeout=step.agent and agent.timeout_sec)
            if event["kind"] == "action_request" and event["agent_id"] == step.agent and event["step"] == step.step:
                try:
                    result = self._execute_action(agent, step, event["action_input"], interactive)
                    self._agent_inbound_queues[step.agent].put({"status": "success", "result": result})
                except Exception as exc:
                    self._agent_inbound_queues[step.agent].put({"status": "failed", "error": str(exc)})
            elif event["kind"] == "step_result" and event["agent_id"] == step.agent and event["step"] == step.step:
                if event["status"] != "success":
                    self.store.update_agent_status(self.session_id, step.agent, AgentStatus.FAILED)
                    raise RuntimeError(event.get("error") or f"step {step.step} failed")
                self.store.update_agent_status(self.session_id, step.agent, AgentStatus.SUCCESS)
                return event["result"]

    def _build_action_request(self, agent: SpawnAgentBlock, step: PipelineStep, action_input: dict[str, Any]) -> ActionRequest:
        tool_name = action_input.get("tool_name") or action_input.get("skill_id")
        file_path = action_input.get("path")
        estimated_tokens = max(1, len(json.dumps(action_input, default=str)) // 4) if step.action_type in {"model_completion", "critic_review"} else 0
        external_call = step.action_type in {"model_completion", "critic_review"} and agent.local_or_cloud == "cloud"
        return ActionRequest(
            type=step.action_type,
            summary=step.task,
            risk_level=step.risk_level,
            tool_name=tool_name,
            file_path=file_path,
            memory_tier=MemoryTier(action_input["tier"]) if "tier" in action_input else None,
            target_agent=action_input.get("target_agent"),
            external_call=external_call,
            requires_critic=step.requires_critic,
            stateful=step.action_type in {"memory_write"} or tool_name in {"file_write", "maya.file_write"},
            estimated_tokens=estimated_tokens,
            estimated_cost=0.0,
            tool_calls=1 if step.action_type == "tool" else 0,
        )

    def _execute_action(self, agent: SpawnAgentBlock, step: PipelineStep, action_input: dict[str, Any], interactive: bool) -> Any:
        request = self._build_action_request(agent, step, action_input)
        decision = self.governance.evaluate_action(agent=agent, request=request, root_intent=self._pipeline.root_intent, current_task=step.task)
        self._audit(
            agent_id=agent.id,
            role=agent.role,
            action_type=step.action_type,
            governance_layer=" | ".join(f"{layer}:{reason}" for layer, reason in decision.layers.items()),
            outcome="approved" if decision.allowed else "denied",
            input_payload={"task": step.task, "action_input": action_input},
            output_payload={"halt_reason": decision.halt_reason, "approval_required": decision.approval_required},
            tool_used=request.tool_name,
        )
        if not decision.allowed:
            if decision.policy_decision and str(decision.policy_decision.action) == "ROLLBACK":
                checkpoints = self.store.list_checkpoints(self.session_id)
                if checkpoints:
                    self.rollback(checkpoints[-1]["checkpoint_id"])
            raise RuntimeError(decision.halt_reason or "governance denied action")

        if decision.approval_required:
            approval = ApprovalRequest(
                session_id=self.session_id,
                agent_id=agent.id,
                risk_level=step.risk_level,
                action_summary=step.task,
                typed_confirmation_required=decision.typed_confirmation_required,
            )
            self.store.create_approval(approval)
            self.store.update_agent_status(self.session_id, agent.id, AgentStatus.PAUSED)
            if not interactive:
                raise RuntimeError(f"approval required: {approval.request_id}")
            self._wait_for_approval(approval.request_id)
            resolved = self.store.get_approval(approval.request_id)
            if resolved["state"] != "approved":
                raise RuntimeError(f"approval denied: {approval.request_id}")
            self.store.update_agent_status(self.session_id, agent.id, AgentStatus.RUNNING)

        if decision.checkpoint_required:
            self.checkpoint(f"pre_{step.action_type}_step_{step.step}")

        result = self._dispatch_action(agent, step, action_input)
        if step.requires_critic and step.action_type != "critic_review":
            result = {"result": result, "critic": self._critic_review(step, result)}
        if step.output_memory_tier:
            self.memory_manager.write(self.session_id, agent.id, step.output_memory_tier, f"step_{step.step}", result)
        actual_request = self._build_action_request(agent, step, action_input)
        if isinstance(result, dict) and "tokens_used" in result:
            actual_request.estimated_tokens = int(result.get("tokens_used", 0))
            actual_request.estimated_cost = float(result.get("cost_usd", 0.0))
        self.governance.record_consumption(agent.id, actual_request)
        return result

    def _dispatch_action(self, agent: SpawnAgentBlock, step: PipelineStep, action_input: dict[str, Any]) -> Any:
        if step.action_type == "model_completion":
            completion = self.model_client.complete(
                model=agent.model,
                fallback_model=agent.fallback_model,
                base_url=agent.base_url,
                system_prompt=agent.system_prompt,
                prompt=action_input.get("prompt", step.task),
            )
            payload = self._completion_payload(completion)
            self._audit(
                agent_id=agent.id,
                role=agent.role,
                action_type="model_completion_result",
                governance_layer="L3-L6",
                outcome="success",
                input_payload={"step": step.step},
                output_payload=payload,
            )
            return payload

        if step.action_type == "tool":
            return self._execute_tool(agent, action_input)

        if step.action_type == "memory_read":
            target_agent = action_input.get("target_agent", agent.id)
            result = self.memory_manager.read(self.session_id, target_agent, MemoryTier(action_input["tier"]), action_input.get("key"))
            self._audit(
                agent_id=agent.id,
                role=agent.role,
                action_type="memory_read",
                governance_layer="L2-L6",
                outcome="success",
                input_payload=action_input,
                output_payload=result,
            )
            return result

        if step.action_type == "memory_write":
            self.memory_manager.write(
                self.session_id,
                action_input.get("target_agent", agent.id),
                MemoryTier(action_input["tier"]),
                action_input["key"],
                action_input["value"],
                action_input.get("metadata"),
            )
            payload = {"written": True, "key": action_input["key"]}
            self._audit(
                agent_id=agent.id,
                role=agent.role,
                action_type="memory_write",
                governance_layer="L2-L7",
                outcome="success",
                input_payload=action_input,
                output_payload=payload,
            )
            return payload

        if step.action_type == "message":
            message = MessageEnvelope.model_validate(action_input)
            self.store.record_message(self.session_id, message)
            payload = {"message_id": message.id}
            self._audit(
                agent_id=agent.id,
                role=agent.role,
                action_type="message",
                governance_layer="L4-L6",
                outcome="success",
                input_payload=action_input,
                output_payload=payload,
            )
            return payload

        if step.action_type == "critic_review":
            return self._critic_review(step, action_input.get("content"))

        if step.action_type == "spawn_agent":
            spawn_block = SpawnAgentBlock.model_validate(action_input["spawn_block"])
            self._spawn_subagent(agent, spawn_block)
            payload = {"agent_id": spawn_block.id}
            self._audit(
                agent_id=agent.id,
                role=agent.role,
                action_type="spawn_agent",
                governance_layer="L2-L6",
                outcome="success",
                input_payload=action_input,
                output_payload=payload,
            )
            return payload

        raise RuntimeError(f"unsupported action type: {step.action_type}")

    def _execute_tool(self, agent: SpawnAgentBlock, action_input: dict[str, Any]) -> Any:
        skill_id = action_input.get("skill_id") or action_input.get("tool_name")
        tool_map = {
            "maya.file_read": "file_read",
            "maya.file_write": "file_write",
            "maya.code_exec": "code_exec",
            "file_read": "file_read",
            "file_write": "file_write",
            "code_exec": "code_exec",
        }
        if skill_id in {"maya.audit_query", "audit_query"}:
            return {"entries": self.audit_entries()}
        if skill_id in {"maya.human_request", "human_request"}:
            approval = ApprovalRequest(
                session_id=self.session_id,
                agent_id=agent.id,
                risk_level=RiskLevel(action_input.get("risk_level", "HIGH")),
                action_summary=action_input.get("summary", "human review requested"),
            )
            self.store.create_approval(approval)
            return approval.model_dump(mode="json")
        mapped_tool = tool_map.get(skill_id)
        if not mapped_tool:
            raise RuntimeError(f"unsupported tool skill: {skill_id}")
        if not self._use_processes:
            payload = self._run_tool_request(
                {
                    "tool_name": mapped_tool,
                    "workdir": str(self.agents_dir / agent.id / "workspace"),
                    "agent_root": str(self.agents_dir / agent.id),
                    "path": action_input.get("path"),
                    "content": action_input.get("content"),
                    "command": action_input.get("command"),
                    "timeout": action_input.get("timeout", 30),
                }
            )
            self._audit(
                agent_id=agent.id,
                role=agent.role,
                action_type="tool_execution",
                governance_layer="L2-L6",
                outcome="success",
                input_payload=action_input,
                output_payload=payload,
                tool_used=mapped_tool,
            )
            return payload
        workdir = str(self.agents_dir / agent.id / "workspace")
        self._tool_request_queue.put(
            {
                "kind": "execute",
                "tool_name": mapped_tool,
                "workdir": workdir,
                "agent_root": str(self.agents_dir / agent.id),
                "path": action_input.get("path"),
                "content": action_input.get("content"),
                "command": action_input.get("command"),
                "timeout": action_input.get("timeout", 30),
            }
        )
        response = self._tool_response_queue.get()
        if response["kind"] == "error":
            raise RuntimeError(response["error"])
        payload = response["result"]
        self._audit(
            agent_id=agent.id,
            role=agent.role,
            action_type="tool_execution",
            governance_layer="L2-L6",
            outcome="success",
            input_payload=action_input,
            output_payload=payload,
            tool_used=mapped_tool,
        )
        return payload

    def _spawn_subagent(self, parent_agent: SpawnAgentBlock, subagent: SpawnAgentBlock) -> None:
        self._agents[subagent.id] = subagent
        ensure_dir(self.agents_dir / subagent.id / "workspace")
        self.store.record_agent(self.session_id, subagent, AgentStatus.RUNNING)
        self.budget_tracker.register_agent(subagent)
        inbound = self._ctx.Queue()
        process = self._ctx.Process(
            target=generic_agent_worker,
            args=(subagent.model_dump(mode="python"), inbound, self._event_queue),
            name=f"maya-agent-{subagent.id}",
        )
        process.start()
        self._agent_inbound_queues[subagent.id] = inbound
        self._agent_processes[subagent.id] = process

    def _run_tool_request(self, request: dict[str, Any]) -> dict[str, Any]:
        workdir = Path(request["workdir"])
        agent_root = Path(request.get("agent_root", workdir))
        path_value = request.get("path")
        path = Path(path_value) if path_value else workdir
        if not path.is_absolute():
            path = agent_root / path
        if not safe_relative_to(path, self.session_dir):
            raise RuntimeError("path escapes tool sandbox")
        if request["tool_name"] == "file_read":
            return {"content": path.read_text(encoding="utf-8"), "path": str(path)}
        if request["tool_name"] == "file_write":
            ensure_dir(path.parent)
            path.write_text(request["content"], encoding="utf-8")
            return {"path": str(path)}
        if request["tool_name"] == "code_exec":
            command = request["command"]
            shell = isinstance(command, str)
            completed = subprocess.run(
                command if shell else list(command),
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=request.get("timeout", 30),
                shell=shell,
            )
            return {
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "returncode": completed.returncode,
            }
        raise RuntimeError(f"unsupported tool: {request['tool_name']}")

    def _critic_review(self, step: PipelineStep, content: Any) -> dict[str, Any]:
        critics = [agent for agent in self._agents.values() if agent.role == AgentRole.CRITIC]
        review_prompt = f"Review this output for quality, safety, and policy issues:\n\n{content}"
        if critics:
            critic = critics[0]
            completion = self.model_client.complete(
                model=critic.model,
                fallback_model=critic.fallback_model,
                base_url=critic.base_url,
                system_prompt=critic.system_prompt,
                prompt=review_prompt,
            )
            payload = {
                "approved": True,
                "review": completion.text,
                "model_used": completion.model_used,
                "fallback_used": completion.fallback_used,
            }
            self._audit(
                agent_id=critic.id,
                role=critic.role,
                action_type="critic_review",
                governance_layer="L5-L6",
                outcome="success",
                input_payload={"step": step.step},
                output_payload=payload,
            )
            return payload
        payload = {"approved": True, "review": "No critic configured; review skipped."}
        self._audit(
            agent_id=step.agent,
            role=self._agents[step.agent].role,
            action_type="critic_review",
            governance_layer="L5-L6",
            outcome="skipped",
            input_payload={"step": step.step},
            output_payload=payload,
        )
        return payload

    @staticmethod
    def _completion_payload(completion: CompletionResult) -> dict[str, Any]:
        return {
            "text": completion.text,
            "tokens_used": completion.tokens_used,
            "cost_usd": completion.cost_usd,
            "model_used": completion.model_used,
            "fallback_used": completion.fallback_used,
        }

    def _wait_for_approval(self, request_id: str) -> None:
        while True:
            approval = self.store.get_approval(request_id)
            if approval and approval["state"] != "pending":
                return
            raw = input(f"maya[{self.session_id}] approval {request_id}> ").strip()
            if not raw:
                continue
            self.handle_runtime_command(raw)

    def handle_runtime_command(self, raw: str) -> Any:
        parts = shlex.split(raw)
        if not parts:
            return None
        command = parts[0].lower()
        if command == "status":
            snapshot = self.status_snapshot()
            print(json.dumps(snapshot, indent=2))
            return snapshot
        if command == "audit":
            entries = self.audit_entries()
            print(json.dumps(entries, indent=2))
            return entries
        if command == "checkpoint":
            reason = parts[1] if len(parts) > 1 else "manual"
            checkpoint = self.checkpoint(reason)
            print(checkpoint.model_dump_json(indent=2))
            return checkpoint
        if command == "rollback":
            checkpoint_id = parts[1]
            checkpoint = self.rollback(checkpoint_id)
            print(json.dumps(checkpoint, indent=2))
            return checkpoint
        if command == "approve":
            confirmation = parts[2] if len(parts) > 2 else None
            approval = self.approve(parts[1], confirmation)
            print(json.dumps(approval, indent=2))
            return approval
        if command == "deny":
            reason = " ".join(parts[2:]) if len(parts) > 2 else None
            denial = self.deny(parts[1], reason)
            print(json.dumps(denial, indent=2))
            return denial
        if command == "pause":
            self.pause(parts[1])
            return None
        if command == "resume":
            self.resume(parts[1])
            return None
        if command == "terminate":
            self.terminate(parts[1])
            return None
        if command == "help":
            print("Commands: status, audit, checkpoint <reason>, rollback <id>, approve <id> [confirmation], deny <id> [reason], pause <agent>, resume <agent>, terminate <agent>")
            return None
        raise ValueError(f"unsupported runtime command: {command}")

    def shutdown(self) -> None:
        for agent_id, queue in self._agent_inbound_queues.items():
            try:
                queue.put({"kind": "terminate"})
            except Exception:
                self.store.update_agent_status(self.session_id, agent_id, AgentStatus.TERMINATED)
        for process in self._agent_processes.values():
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
        if self._tool_request_queue is not None and self._tool_response_queue is not None:
            self._tool_request_queue.put({"kind": "close"})
            self._tool_response_queue.get()
        if self._tool_process is not None:
            self._tool_process.join(timeout=2)
            if self._tool_process.is_alive():
                self._tool_process.terminate()
        if self._audit_client is not None:
            self._audit_client.close()
        if self._audit_process is not None:
            self._audit_process.join(timeout=2)
            if self._audit_process.is_alive():
                self._audit_process.terminate()


class OfflineSessionAdmin:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.store = PersistenceStore(session_dir / "state.sqlite3")
        self.audit_log = AuditLog(session_dir / "audit.jsonl")
        self.checkpoint_manager = CheckpointManager(session_dir, self.store)

    def status(self, session_id: str) -> dict[str, Any]:
        return {
            "session": self.store.get_session(session_id),
            "agents": self.store.list_agents(session_id),
            "approvals": self.store.list_approvals(session_id),
            "checkpoints": self.store.list_checkpoints(session_id),
        }

    def audit(self) -> list[dict[str, Any]]:
        return self.audit_log.entries()

    def checkpoint(self, session_id: str, reason: str) -> CheckpointRecord:
        return self.checkpoint_manager.create(session_id, reason, {"session": self.store.get_session(session_id)})

    def rollback(self, checkpoint_id: str) -> dict[str, Any]:
        return self.checkpoint_manager.rollback(checkpoint_id)

    def approve(self, request_id: str, confirmation: str | None = None) -> dict[str, Any]:
        approval = self.store.get_approval(request_id)
        if not approval:
            raise ValueError(f"approval '{request_id}' not found")
        if approval["typed_confirmation_required"] and confirmation != request_id:
            raise ValueError("typed confirmation must match the request id")
        self.store.update_approval(request_id, "approved", "approved offline")
        return self.store.get_approval(request_id)

    def deny(self, request_id: str, reason: str | None = None) -> dict[str, Any]:
        approval = self.store.get_approval(request_id)
        if not approval:
            raise ValueError(f"approval '{request_id}' not found")
        self.store.update_approval(request_id, "denied", reason or "denied offline")
        return self.store.get_approval(request_id)

    def update_agent_status(self, session_id: str, agent_id: str, status: str) -> None:
        self.store.update_agent_status(session_id, agent_id, status)
