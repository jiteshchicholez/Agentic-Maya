from __future__ import annotations

import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from myna.loader import load_pipeline
from myna.schemas import SpawnAgentBlock


class SchemaTests(unittest.TestCase):
    def test_spawn_agent_requires_fallback_model(self) -> None:
        with self.assertRaises(ValidationError):
            SpawnAgentBlock.model_validate(
                {
                    "id": "agent",
                    "role": "SPECIALIST",
                    "model": "demo-model",
                    "fallback_model": "",
                    "base_url": "http://localhost:11434/v1",
                    "provider": "openai_compatible",
                    "local_or_cloud": "local",
                    "system_prompt": "test",
                    "permissions": {"tools": [], "memory": "read", "spawn_agents": False, "external_calls": False, "file_access": []},
                    "budget": {
                        "max_tokens_per_agent": 10,
                        "max_tool_calls": 5,
                        "max_cost_usd": 1.0,
                        "max_wall_time_sec": 30,
                    },
                }
            )

    def test_demo_pipeline_loads(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        pipeline = load_pipeline(project_root / "pipelines" / "document_review.yml")
        self.assertEqual(pipeline.id, "document_review")
        self.assertEqual(pipeline.orchestrator, "review_orchestrator")
        self.assertEqual(len(pipeline.agents), 3)
        self.assertGreater(len(pipeline.flow), 0)


if __name__ == "__main__":
    unittest.main()
