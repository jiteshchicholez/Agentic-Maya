from enum import StrEnum


class AgentRole(StrEnum):
    ORCHESTRATOR = "ORCHESTRATOR"
    SPECIALIST = "SPECIALIST"
    SUBAGENT = "SUBAGENT"
    CRITIC = "CRITIC"
    MEMORY_MGR = "MEMORY_MGR"
    TOOL_EXEC = "TOOL_EXEC"
    AUDIT_AGENT = "AUDIT_AGENT"


class MemoryAccess(StrEnum):
    NONE = "none"
    READ = "read"
    WRITE = "write"


class MemoryTier(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PERSISTENT = "persistent"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MessageType(StrEnum):
    TASK = "TASK"
    RESULT = "RESULT"
    ERROR = "ERROR"
    STATUS = "STATUS"
    REQUEST = "REQUEST"
    APPROVE = "APPROVE"


class Priority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class ActionType(StrEnum):
    MODEL_COMPLETION = "model_completion"
    TOOL = "tool"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    MESSAGE = "message"
    CRITIC_REVIEW = "critic_review"
    SPAWN_AGENT = "spawn_agent"


class PolicyScope(StrEnum):
    GLOBAL = "GLOBAL"
    PIPELINE = "PIPELINE"
    AGENT = "AGENT"
    SKILL = "SKILL"


class PolicyAction(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    WARN = "WARN"
    ESCALATE = "ESCALATE"
    HALT = "HALT"
    ROLLBACK = "ROLLBACK"


class AgentStatus(StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    POLICY_HALT = "POLICY_HALT"
    TIMEOUT = "TIMEOUT"


class PipelineStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class LocalOrCloud(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"
