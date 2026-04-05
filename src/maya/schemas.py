from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from maya.enums import (
    AgentRole,
    LocalOrCloud,
    MemoryAccess,
    MemoryTier,
    MessageType,
    PolicyAction,
    PolicyScope,
    Priority,
    RiskLevel,
)
from maya.utils import utc_now


class PermissionsBlock(BaseModel):
    tools: list[str] = Field(default_factory=list)
    memory: MemoryAccess = MemoryAccess.NONE
    spawn_agents: bool = False
    external_calls: bool = False
    file_access: list[str] = Field(default_factory=list)

    @field_validator("tools", "file_access")
    @classmethod
    def dedupe_lists(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class BudgetBlock(BaseModel):
    max_tokens_per_agent: int = 32000
    max_tool_calls: int = 50
    max_cost_usd: float = 2.0
    max_wall_time_sec: int = 300

    @model_validator(mode="after")
    def validate_positive(self) -> "BudgetBlock":
        if self.max_tokens_per_agent <= 0 or self.max_tool_calls <= 0 or self.max_wall_time_sec <= 0:
            raise ValueError("budget limits must be positive")
        if self.max_cost_usd < 0:
            raise ValueError("max_cost_usd cannot be negative")
        return self


class GlobalBudgetBlock(BaseModel):
    max_total_tokens: int = 200000
    max_total_cost_usd: float = 10.0
    max_total_time_sec: int = 1800


class SpawnAgentBlock(BaseModel):
    id: str
    role: AgentRole
    model: str
    fallback_model: str
    base_url: str
    provider: str
    local_or_cloud: LocalOrCloud
    system_prompt: str
    skills: list[str] = Field(default_factory=list)
    memory_tier: MemoryTier = MemoryTier.WORKING
    permissions: PermissionsBlock
    budget: BudgetBlock
    parent_agent: str | None = None
    max_subagents: int = 0
    timeout_sec: int = 300

    @model_validator(mode="after")
    def validate_model_config(self) -> "SpawnAgentBlock":
        if not self.model.strip():
            raise ValueError("model is required")
        if not self.fallback_model.strip():
            raise ValueError("fallback_model is required")
        if not self.base_url.strip():
            raise ValueError("base_url is required")
        if not self.provider.strip():
            raise ValueError("provider is required")
        return self


class MessageEnvelope(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    from_agent: str = Field(alias="from")
    to: str
    type: MessageType
    payload: dict[str, Any] | list[Any] | str
    priority: Priority = Priority.NORMAL
    requires_ack: bool = False


class SkillDefinition(BaseModel):
    id: str
    name: str
    version: str
    description: str
    inputs: list[dict[str, Any] | str] = Field(default_factory=list)
    outputs: list[dict[str, Any] | str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    governance_level: RiskLevel = RiskLevel.LOW
    author: str
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True


class PolicyDefinition(BaseModel):
    id: str
    name: str
    scope: PolicyScope
    trigger: dict[str, Any]
    action: PolicyAction
    message: str
    log_level: str = "INFO"
    notify_human: bool = False
    enabled: bool = True


class PipelineStep(BaseModel):
    step: int
    agent: str
    task: str
    depends_on: list[int] = Field(default_factory=list)
    on_success: str = "next_step"
    on_failure: str = "rollback"
    risk_level: RiskLevel = RiskLevel.LOW
    requires_critic: bool = False
    action_type: Literal[
        "model_completion",
        "tool",
        "memory_read",
        "memory_write",
        "message",
        "critic_review",
        "spawn_agent",
    ] = "model_completion"
    action_input: dict[str, Any] = Field(default_factory=dict)
    output_memory_tier: MemoryTier | None = None


class PipelineDefinition(BaseModel):
    id: str
    name: str
    description: str
    trigger: str
    orchestrator: str
    root_intent: str
    agents: list[SpawnAgentBlock]
    flow: list[PipelineStep]
    global_budget: GlobalBudgetBlock = Field(default_factory=GlobalBudgetBlock)
    global_policies: list[str] = Field(default_factory=list)
    on_complete: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pipeline(self) -> "PipelineDefinition":
        agent_ids = {agent.id for agent in self.agents}
        if self.orchestrator not in agent_ids:
            raise ValueError("orchestrator must be a declared agent")
        for step in self.flow:
            if step.agent not in agent_ids:
                raise ValueError(f"step agent '{step.agent}' is not declared")
        return self


class AuditEntry(BaseModel):
    timestamp: str = Field(default_factory=utc_now)
    agent_id: str
    role: str
    action_type: str
    tool_used: str | None = None
    input_hash: str = ""
    output_hash: str = ""
    governance_layer: str
    outcome: str
    details: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str | None = None
    entry_hash: str | None = None


class CheckpointRecord(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    created_at: str = Field(default_factory=utc_now)
    reason: str
    db_snapshot_path: str
    workdir_snapshot_path: str
    pipeline_state: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    agent_id: str
    risk_level: RiskLevel
    action_summary: str
    state: Literal["pending", "approved", "denied"] = "pending"
    created_at: str = Field(default_factory=utc_now)
    resolved_at: str | None = None
    resolution: str | None = None
    typed_confirmation_required: bool = False


class MessageSchema(BaseModel):
    from_agent: str
    to_agent: str
    type: MessageType
    payload: dict[str, Any] | list[Any] | str
    priority: Priority = Priority.NORMAL
    requires_ack: bool = False


class CheckpointSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    label: str
    agent_states: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


AgentConfig = SpawnAgentBlock
BudgetConfig = BudgetBlock
PermissionsConfig = PermissionsBlock
PipelineConfig = PipelineDefinition
PolicySchema = PolicyDefinition
SkillSchema = SkillDefinition
