from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maya.config import AppConfig
from maya.model_client import FakeModelClient
from maya.runtime import SessionRuntime
from maya.schemas import PipelineDefinition


def build_runtime_pipeline() -> PipelineDefinition:
    return PipelineDefinition.model_validate(
        {
            "id": "runtime_test",
            "name": "Runtime Test",
            "description": "Exercise the runtime with fallback and critic review.",
            "trigger": "test",
            "root_intent": "Create a governed runtime test report",
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
                    "budget": {"max_tokens_per_agent": 200, "max_tool_calls": 20, "max_cost_usd": 2.0, "max_wall_time_sec": 60},
                },
                {
                    "id": "specialist",
                    "role": "SPECIALIST",
                    "model": "primary-model",
                    "fallback_model": "backup-model",
                    "base_url": "http://localhost:11434/v1",
                    "provider": "openai_compatible",
                    "local_or_cloud": "local",
                    "system_prompt": "Draft technical summaries.",
                    "permissions": {"tools": ["maya.file_write"], "memory": "write", "spawn_agents": False, "external_calls": False, "file_access": ["workspace"]},
                    "budget": {"max_tokens_per_agent": 200, "max_tool_calls": 20, "max_cost_usd": 2.0, "max_wall_time_sec": 60},
                },
                {
                    "id": "critic",
                    "role": "CRITIC",
                    "model": "critic-model",
                    "fallback_model": "critic-model",
                    "base_url": "http://localhost:11434/v1",
                    "provider": "openai_compatible",
                    "local_or_cloud": "local",
                    "system_prompt": "Review outputs.",
                    "permissions": {"tools": [], "memory": "read", "spawn_agents": False, "external_calls": False, "file_access": ["workspace"]},
                    "budget": {"max_tokens_per_agent": 200, "max_tool_calls": 20, "max_cost_usd": 2.0, "max_wall_time_sec": 60},
                },
                {
                    "id": "tool_exec",
                    "role": "TOOL_EXEC",
                    "model": "tool-model",
                    "fallback_model": "tool-model",
                    "base_url": "http://localhost:11434/v1",
                    "provider": "openai_compatible",
                    "local_or_cloud": "local",
                    "system_prompt": "Execute tools.",
                    "permissions": {"tools": ["maya.file_write"], "memory": "none", "spawn_agents": False, "external_calls": False, "file_access": ["workspace"]},
                    "budget": {"max_tokens_per_agent": 200, "max_tool_calls": 20, "max_cost_usd": 2.0, "max_wall_time_sec": 60},
                },
                {
                    "id": "audit_agent",
                    "role": "AUDIT_AGENT",
                    "model": "audit-model",
                    "fallback_model": "audit-model",
                    "base_url": "http://localhost:11434/v1",
                    "provider": "openai_compatible",
                    "local_or_cloud": "local",
                    "system_prompt": "Observe.",
                    "permissions": {"tools": [], "memory": "none", "spawn_agents": False, "external_calls": False, "file_access": ["workspace"]},
                    "budget": {"max_tokens_per_agent": 200, "max_tool_calls": 20, "max_cost_usd": 2.0, "max_wall_time_sec": 60},
                },
            ],
            "flow": [
                {
                    "step": 1,
                    "agent": "specialist",
                    "task": "Create a governed runtime test report",
                    "risk_level": "LOW",
                    "action_type": "model_completion",
                    "action_input": {"prompt": "Create a governed runtime test report"},
                    "output_memory_tier": "episodic",
                },
                {
                    "step": 2,
                    "agent": "specialist",
                    "task": "Persist the runtime test report",
                    "depends_on": [1],
                    "risk_level": "LOW",
                    "requires_critic": True,
                    "action_type": "tool",
                    "action_input": {
                        "skill_id": "maya.file_write",
                        "path": "workspace/report.txt",
                        "content": "{{step:1.text}}",
                    },
                },
            ],
            "global_budget": {"max_total_tokens": 1000, "max_total_cost_usd": 10.0, "max_total_time_sec": 600},
        }
    )


class RuntimeTests(unittest.TestCase):
    def test_runtime_executes_pipeline_with_fallback_and_critic(self) -> None:
        workspace_root = Path(__file__).resolve().parents[1]
        project_root = workspace_root / ".test_artifacts" / f"runtime_{uuid4().hex}"
        project_root.mkdir(parents=True, exist_ok=False)
        try:
            runtime = SessionRuntime(
                project_root=project_root,
                config=AppConfig(),
                model_client=FakeModelClient(
                    completions={
                        "backup-model": "Governed runtime summary.",
                        "critic-model": "Looks compliant.",
                    },
                    fail_primary_models={"primary-model"},
                ),
            )
            report = runtime.run_pipeline(build_runtime_pipeline(), interactive=False)
            self.assertEqual(report.status, "SUCCESS")
            self.assertTrue(report.step_outputs[1]["fallback_used"])
            self.assertEqual(report.step_outputs[1]["model_used"], "backup-model")
            self.assertIn("critic", report.step_outputs[2])
            written = project_root / ".maya" / "sessions" / report.session_id / "agents" / "specialist" / "workspace" / "report.txt"
            self.assertTrue(written.exists())
            self.assertEqual(written.read_text(encoding="utf-8"), "Governed runtime summary.")
        finally:
            shutil.rmtree(project_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
