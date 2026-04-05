from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from myna.enums import MemoryTier
from myna.schemas import ApprovalRequest, CheckpointRecord, MessageEnvelope, PolicyDefinition, SkillDefinition, SpawnAgentBlock
from myna.utils import ensure_dir, utc_now


class PersistenceStore:
    def __init__(self, db_path: Path | None = None, project_root: Path | None = None):
        self._persistent_connection: sqlite3.Connection | None = None
        if db_path is not None:
            self.db_path = db_path
        elif project_root is not None:
            self.db_path = project_root / ".myna" / "myna.db"
        else:
            self.db_path = Path(":memory:")
            self._persistent_connection = sqlite3.connect(str(self.db_path))
            self._persistent_connection.row_factory = sqlite3.Row
        ensure_dir(self.db_path.parent)
        self._initialize_schema()

    @contextmanager
    def connection(self):
        if self._persistent_connection is not None:
            try:
                yield self._persistent_connection
                self._persistent_connection.commit()
            finally:
                return
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize_schema(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    root_intent TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agents (
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    parent_agent TEXT,
                    model TEXT NOT NULL,
                    fallback_model TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    local_or_cloud TEXT NOT NULL,
                    PRIMARY KEY (session_id, agent_id)
                );
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    requires_ack INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    request_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    action_summary TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    resolution TEXT,
                    typed_confirmation_required INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    reason TEXT,
                    label TEXT,
                    created_at TEXT NOT NULL,
                    db_snapshot_path TEXT,
                    workdir_snapshot_path TEXT,
                    pipeline_state_json TEXT,
                    agent_states_json TEXT
                );
                CREATE TABLE IF NOT EXISTS skills (
                    skill_id TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    definition_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS policies (
                    policy_id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    action TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    definition_json TEXT NOT NULL
                );
                """
            )

    def create_session(self, session_id: str, pipeline_id: str, root_intent: str, status: str) -> None:
        now = utc_now()
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO sessions (session_id, pipeline_id, root_intent, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, pipeline_id, root_intent, status, now, now),
            )

    def init_session(self, session_id: str, pipeline_id: str, root_intent: str = "") -> None:
        self.create_session(session_id, pipeline_id, root_intent, "CREATED")

    def update_session_status(self, session_id: str, status: str) -> None:
        with self.connection() as connection:
            connection.execute(
                "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                (status, utc_now(), session_id),
            )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return dict(row) if row else None

    def record_agent(self, session_id: str, agent: SpawnAgentBlock, status: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO agents (
                    session_id, agent_id, role, status, parent_agent, model, fallback_model, provider, local_or_cloud
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    agent.id,
                    agent.role,
                    status,
                    agent.parent_agent,
                    agent.model,
                    agent.fallback_model,
                    agent.provider,
                    agent.local_or_cloud,
                ),
            )

    def register_agent(self, session_id: str, agent: SpawnAgentBlock, status: str = "IDLE") -> None:
        self.record_agent(session_id, agent, status)

    def get_agent(self, session_id: str, agent_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM agents WHERE session_id = ? AND agent_id = ?",
                (session_id, agent_id),
            ).fetchone()
        return dict(row) if row else None

    def update_agent_status(self, session_id: str, agent_id: str, status: str) -> None:
        with self.connection() as connection:
            connection.execute(
                "UPDATE agents SET status = ? WHERE session_id = ? AND agent_id = ?",
                (status, session_id, agent_id),
            )

    def list_agents(self, session_id: str) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM agents WHERE session_id = ? ORDER BY agent_id",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_message(self, session_id: str, message: MessageEnvelope) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO messages (
                    message_id, session_id, from_agent, to_agent, type, payload_json, priority, requires_ack, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    session_id,
                    message.from_agent,
                    message.to,
                    message.type,
                    json.dumps(message.payload),
                    message.priority,
                    int(message.requires_ack),
                    utc_now(),
                ),
            )

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at, message_id",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_approval(self, approval: ApprovalRequest) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO approvals (
                    request_id, session_id, agent_id, risk_level, action_summary, state,
                    created_at, resolved_at, resolution, typed_confirmation_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval.request_id,
                    approval.session_id,
                    approval.agent_id,
                    approval.risk_level,
                    approval.action_summary,
                    approval.state,
                    approval.created_at,
                    approval.resolved_at,
                    approval.resolution,
                    int(approval.typed_confirmation_required),
                ),
            )

    def update_approval(self, request_id: str, state: str, resolution: str | None = None) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE approvals
                SET state = ?, resolved_at = ?, resolution = ?
                WHERE request_id = ?
                """,
                (state, utc_now(), resolution, request_id),
            )

    def get_approval(self, request_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM approvals WHERE request_id = ?", (request_id,)).fetchone()
        return dict(row) if row else None

    def list_approvals(self, session_id: str, state: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM approvals WHERE session_id = ?"
        params: list[Any] = [session_id]
        if state:
            query += " AND state = ?"
            params.append(state)
        query += " ORDER BY created_at, request_id"
        with self.connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def write_memory(
        self,
        session_id: str,
        agent_id: str,
        tier: str,
        key: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO memory_entries (session_id, agent_id, tier, key, value_json, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    agent_id,
                    tier,
                    key,
                    json.dumps(value),
                    json.dumps(metadata or {}),
                    utc_now(),
                ),
            )

    def read_memory(
        self,
        session_id: str,
        tier: str,
        agent_id: str | None = None,
        key: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM memory_entries WHERE session_id = ? AND tier = ?"
        params: list[Any] = [session_id, tier]
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        if key:
            query += " AND key = ?"
            params.append(key)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self.connection() as connection:
            rows = connection.execute(query, params).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["value"] = json.loads(item.pop("value_json"))
            item["metadata"] = json.loads(item.pop("metadata_json"))
            result.append(item)
        return result

    def create_checkpoint(self, checkpoint: CheckpointRecord | None = None, *, session_id: str | None = None, label: str | None = None, agent_states: dict[str, Any] | None = None, created_at: str | None = None) -> str | None:
        if checkpoint is not None:
            with self.connection() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO checkpoints (
                        checkpoint_id, session_id, reason, created_at, db_snapshot_path, workdir_snapshot_path, pipeline_state_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        checkpoint.checkpoint_id,
                        checkpoint.session_id,
                        checkpoint.reason,
                        checkpoint.created_at,
                        checkpoint.db_snapshot_path,
                        checkpoint.workdir_snapshot_path,
                        json.dumps(checkpoint.pipeline_state),
                    ),
                )
            return None
        if session_id is None or label is None or agent_states is None:
            raise ValueError("session_id, label, and agent_states are required for checkpoint creation")
        checkpoint_id = str(uuid4())
        created_at = created_at or utc_now()
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO checkpoints (
                    checkpoint_id, session_id, label, created_at, agent_states_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    session_id,
                    label,
                    created_at,
                    json.dumps(agent_states),
                ),
            )
        return checkpoint_id

    def get_checkpoint(self, checkpoint_id: str, alias_checkpoint_id: str | None = None) -> dict[str, Any] | None:
        if alias_checkpoint_id is not None:
            checkpoint_id = alias_checkpoint_id
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        if item.get("pipeline_state_json") is not None:
            item["pipeline_state"] = json.loads(item.pop("pipeline_state_json"))
        if item.get("agent_states_json") is not None:
            item["agent_states"] = json.loads(item.pop("agent_states_json"))
        return item

    def list_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY created_at, checkpoint_id",
                (session_id,),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            if item.get("pipeline_state_json") is not None:
                item["pipeline_state"] = json.loads(item.pop("pipeline_state_json"))
            if item.get("agent_states_json") is not None:
                item["agent_states"] = json.loads(item.pop("agent_states_json"))
            items.append(item)
        return items

    def rollback(self, session_id: str, checkpoint_id: str, memory_manager: Any) -> None:
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"checkpoint '{checkpoint_id}' not found")
        agent_states = checkpoint.get("agent_states", {})
        for agent_id, state in agent_states.items():
            for key, value in state.items():
                memory_manager.write(agent_id=agent_id, tier=MemoryTier.EPISODIC, key=key, value=value, session_id=session_id)

    def upsert_skill(self, skill: SkillDefinition, source_path: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO skills (skill_id, version, source_path, enabled, definition_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (skill.id, skill.version, source_path, int(skill.enabled), skill.model_dump_json()),
            )

    def list_skills(self) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM skills ORDER BY skill_id").fetchall()
        return [dict(row) for row in rows]

    def upsert_policy(self, policy: PolicyDefinition, source_path: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO policies (policy_id, scope, action, source_path, enabled, definition_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (policy.id, policy.scope, policy.action, source_path, int(policy.enabled), policy.model_dump_json()),
            )

    def list_policies(self) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM policies ORDER BY policy_id").fetchall()
        return [dict(row) for row in rows]


SessionStore = PersistenceStore
