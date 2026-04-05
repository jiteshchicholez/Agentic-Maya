from __future__ import annotations

from pathlib import Path

from maya.loader import load_directory_models, load_skill
from maya.persistence import PersistenceStore
from maya.schemas import SkillDefinition


def builtin_skills() -> list[SkillDefinition]:
    return [
        SkillDefinition(
            id="maya.web_search",
            name="Web Search",
            version="1.0.0",
            description="Search the web. Disabled until a search adapter is configured.",
            inputs=["query"],
            outputs=["results"],
            required_tools=["web_search"],
            required_permissions=["external_calls"],
            governance_level="HIGH",
            author="agentic-maya",
            tags=["web", "search"],
            enabled=False,
        ),
        SkillDefinition(
            id="maya.code_exec",
            name="Code Execution",
            version="1.0.0",
            description="Execute code or shell commands in the sandboxed tool executor.",
            inputs=["command"],
            outputs=["stdout", "stderr", "returncode"],
            required_tools=["code_exec"],
            required_permissions=["tools", "file_access"],
            governance_level="HIGH",
            author="agentic-maya",
            tags=["tool", "execution"],
        ),
        SkillDefinition(
            id="maya.file_read",
            name="File Read",
            version="1.0.0",
            description="Read files from permitted paths.",
            inputs=["path"],
            outputs=["content"],
            required_tools=["file_read"],
            required_permissions=["file_access"],
            governance_level="LOW",
            author="agentic-maya",
            tags=["tool", "filesystem"],
        ),
        SkillDefinition(
            id="maya.file_write",
            name="File Write",
            version="1.0.0",
            description="Write files into a namespaced sandbox path.",
            inputs=["path", "content"],
            outputs=["path"],
            required_tools=["file_write"],
            required_permissions=["file_access"],
            governance_level="HIGH",
            author="agentic-maya",
            tags=["tool", "filesystem"],
        ),
        SkillDefinition(
            id="maya.memory_read",
            name="Memory Read",
            version="1.0.0",
            description="Read from an agent memory tier.",
            inputs=["tier", "key"],
            outputs=["entries"],
            required_tools=[],
            required_permissions=["memory"],
            governance_level="LOW",
            author="agentic-maya",
            tags=["memory"],
        ),
        SkillDefinition(
            id="maya.memory_write",
            name="Memory Write",
            version="1.0.0",
            description="Write to an agent memory tier.",
            inputs=["tier", "key", "value"],
            outputs=["written"],
            required_tools=[],
            required_permissions=["memory"],
            governance_level="MEDIUM",
            author="agentic-maya",
            tags=["memory"],
        ),
        SkillDefinition(
            id="maya.agent_spawn",
            name="Agent Spawn",
            version="1.0.0",
            description="Spawn a governed subagent.",
            inputs=["spawn_block"],
            outputs=["agent_id"],
            required_tools=[],
            required_permissions=["spawn_agents"],
            governance_level="HIGH",
            author="agentic-maya",
            tags=["agent"],
        ),
        SkillDefinition(
            id="maya.agent_message",
            name="Agent Message",
            version="1.0.0",
            description="Send a message over the maya message bus.",
            inputs=["message"],
            outputs=["message_id"],
            required_tools=[],
            required_permissions=[],
            governance_level="LOW",
            author="agentic-maya",
            tags=["agent", "message"],
        ),
        SkillDefinition(
            id="maya.rag_query",
            name="RAG Query",
            version="1.0.0",
            description="Query semantic memory via vector similarity.",
            inputs=["query"],
            outputs=["matches"],
            required_tools=[],
            required_permissions=["memory"],
            governance_level="MEDIUM",
            author="agentic-maya",
            tags=["memory", "vector"],
        ),
        SkillDefinition(
            id="maya.critic_review",
            name="Critic Review",
            version="1.0.0",
            description="Invoke a critic review over prior output.",
            inputs=["content"],
            outputs=["review"],
            required_tools=[],
            required_permissions=[],
            governance_level="HIGH",
            author="agentic-maya",
            tags=["critic", "review"],
        ),
        SkillDefinition(
            id="maya.human_request",
            name="Human Request",
            version="1.0.0",
            description="Create a human approval request for a gated action.",
            inputs=["summary"],
            outputs=["request_id"],
            required_tools=[],
            required_permissions=[],
            governance_level="HIGH",
            author="agentic-maya",
            tags=["approval", "human"],
        ),
        SkillDefinition(
            id="maya.audit_query",
            name="Audit Query",
            version="1.0.0",
            description="Query the audit log in read-only mode.",
            inputs=["filter"],
            outputs=["entries"],
            required_tools=[],
            required_permissions=[],
            governance_level="LOW",
            author="agentic-maya",
            tags=["audit"],
        ),
        SkillDefinition(
            id="maya.data_query",
            name="Data Query",
            version="1.0.0",
            description="Query structured data sources like databases or APIs.",
            inputs=["query", "source"],
            outputs=["results"],
            required_tools=["data_query"],
            required_permissions=["external_calls"],
            governance_level="MEDIUM",
            author="agentic-maya",
            tags=["data", "query"],
        ),
        SkillDefinition(
            id="maya.frontend_design",
            name="Frontend Design",
            version="1.0.0",
            description="Design and generate frontend components and layouts.",
            inputs=["requirements"],
            outputs=["design", "code"],
            required_tools=["frontend_design"],
            required_permissions=["file_access"],
            governance_level="MEDIUM",
            author="agentic-maya",
            tags=["frontend", "design"],
        ),
        SkillDefinition(
            id="maya.report_writer",
            name="Report Writer",
            version="1.0.0",
            description="Generate structured reports from data and analysis.",
            inputs=["data", "template"],
            outputs=["report"],
            required_tools=["report_writer"],
            required_permissions=["file_access"],
            governance_level="LOW",
            author="agentic-maya",
            tags=["reporting", "writing"],
        ),
    ]


class SkillRegistry:
    def __init__(self, store: PersistenceStore | None = None):
        self.store = store or PersistenceStore()
        self._skills: dict[str, SkillDefinition] = {}

    def seed_builtin_skills(self) -> None:
        for skill in builtin_skills():
            self.register(skill, "builtin")

    seed_builtins = seed_builtin_skills

    def register(self, skill: SkillDefinition, source_path: str = "builtin") -> None:
        if skill.id in self._skills:
            raise ValueError(f"skill '{skill.id}' is already registered")
        self._skills[skill.id] = skill
        self.store.upsert_skill(skill, source_path)

    def load_directory(self, directory: Path) -> None:
        for skill in load_directory_models(directory, load_skill):
            self.register(skill, str(directory))

    def get(self, skill_id: str) -> SkillDefinition:
        return self._skills[skill_id]

    def list(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def find_by_tag(self, tag: str) -> list[SkillDefinition]:
        return [skill for skill in self._skills.values() if any(tag in skill_tag for skill_tag in skill.tags)]
