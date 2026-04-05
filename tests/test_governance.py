from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from myna.governance import ActionRequest, BudgetTracker, GovernanceEngine
from myna.policy import PolicyEngine, builtin_policies
from myna.schemas import GlobalBudgetBlock, SpawnAgentBlock


def build_agent() -> SpawnAgentBlock:
    return SpawnAgentBlock.model_validate(
        {
            "id": "specialist",
            "role": "SPECIALIST",
            "model": "primary-model",
            "fallback_model": "backup-model",
            "base_url": "http://localhost:11434/v1",
            "provider": "openai_compatible",
            "local_or_cloud": "local",
            "system_prompt": "test",
            "permissions": {
                "tools": ["myna.file_write"],
                "memory": "write",
                "spawn_agents": False,
                "external_calls": False,
                "file_access": ["workspace"],
            },
            "budget": {
                "max_tokens_per_agent": 50,
                "max_tool_calls": 5,
                "max_cost_usd": 1.0,
                "max_wall_time_sec": 60,
            },
        }
    )


class GovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = build_agent()
        tracker = BudgetTracker(GlobalBudgetBlock())
        tracker.register_agent(self.agent)
        self.engine = GovernanceEngine(PolicyEngine(builtin_policies()), tracker, Path("sandbox"))

    def test_intent_mismatch_is_denied(self) -> None:
        decision = self.engine.evaluate_action(
            agent=self.agent,
            request=ActionRequest(type="model_completion", summary="Delete production database", risk_level="LOW"),
            root_intent="Write a governed summary report",
            current_task="Summarize the runtime",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.halt_reason, "intent mismatch")

    def test_sibling_memory_reads_are_denied(self) -> None:
        decision = self.engine.evaluate_action(
            agent=self.agent,
            request=ActionRequest(
                type="memory_read",
                summary="Read sibling memory for debugging",
                risk_level="LOW",
                target_agent="other-agent",
            ),
            root_intent="Read sibling memory for debugging",
            current_task="Read sibling memory for debugging",
        )
        self.assertFalse(decision.allowed)
        self.assertIn("sibling memory", decision.halt_reason)

    def test_critical_actions_require_typed_confirmation(self) -> None:
        decision = self.engine.evaluate_action(
            agent=self.agent,
            request=ActionRequest(type="memory_write", summary="Store the critical approval marker", risk_level="CRITICAL", stateful=True),
            root_intent="Store the critical approval marker",
            current_task="Store the critical approval marker",
        )
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.approval_required)
        self.assertTrue(decision.typed_confirmation_required)

    def test_tool_path_outside_workspace_is_denied(self) -> None:
        decision = self.engine.evaluate_action(
            agent=self.agent,
            request=ActionRequest(
                type="tool",
                summary="Write a report file",
                risk_level="LOW",
                tool_name="myna.file_write",
                file_path="..\\escape.txt",
            ),
            root_intent="Write a report file",
            current_task="Write a report file",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.halt_reason, "sandbox violation")


if __name__ == "__main__":
    unittest.main()
