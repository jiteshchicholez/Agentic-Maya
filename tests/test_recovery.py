from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from myna.config import AppConfig
from myna.enums import MemoryTier
from myna.model_client import FakeModelClient
from myna.runtime import SessionRuntime
from myna.schemas import PipelineDefinition


def build_minimal_pipeline() -> PipelineDefinition:
    return PipelineDefinition.model_validate(
        {
            "id": "recovery_test",
            "name": "Recovery Test",
            "description": "Minimal pipeline for checkpoint recovery tests.",
            "trigger": "test",
            "root_intent": "Maintain recoverable session state",
            "orchestrator": "orchestrator",
            "agents": [
                {
                    "id": "orchestrator",
                    "role": "ORCHESTRATOR",
                    "model": "orchestrator-model",
                    "fallback_model": "orchestrator-model",
                    "base_url": "http://localhost:11434/v1",
                    "provider": "openai_compatible",
                    "local_or_cloud": "local",
                    "system_prompt": "Coordinate.",
                    "permissions": {"tools": [], "memory": "write", "spawn_agents": True, "external_calls": False, "file_access": ["workspace"]},
                    "budget": {"max_tokens_per_agent": 100, "max_tool_calls": 10, "max_cost_usd": 1.0, "max_wall_time_sec": 60},
                }
            ],
            "flow": [],
            "global_budget": {"max_total_tokens": 1000, "max_total_cost_usd": 10.0, "max_total_time_sec": 600},
        }
    )


class RecoveryTests(unittest.TestCase):
    def test_checkpoint_and_rollback_restore_state_and_audit_chain(self) -> None:
        workspace_root = Path(__file__).resolve().parents[1]
        project_root = workspace_root / ".test_artifacts" / f"recovery_{uuid4().hex}"
        project_root.mkdir(parents=True, exist_ok=False)
        runtime = SessionRuntime(
            project_root=project_root,
            config=AppConfig(),
            model_client=FakeModelClient(),
            session_id="recovery-session",
        )
        try:
            runtime.initialize(build_minimal_pipeline())
            runtime.memory_manager.write(agent_id="orchestrator", tier=MemoryTier.EPISODIC, key="state", value="before", session_id=runtime.session_id)
            checkpoint = runtime.checkpoint("before-change")
            runtime.memory_manager.write(agent_id="orchestrator", tier=MemoryTier.EPISODIC, key="state", value="after", session_id=runtime.session_id)
            runtime.rollback(checkpoint.checkpoint_id)
            memory_entries = runtime.store.read_memory(runtime.session_id, "episodic", agent_id="orchestrator", key="state", limit=10)
            self.assertEqual(memory_entries[0]["value"], "before")
            entries = runtime.audit_entries()
            previous_hash = None
            for entry in entries:
                self.assertEqual(entry["previous_hash"], previous_hash)
                previous_hash = entry["entry_hash"]
        finally:
            runtime.shutdown()
            shutil.rmtree(project_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
