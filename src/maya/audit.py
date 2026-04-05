from __future__ import annotations

import json
from multiprocessing.queues import Queue
from pathlib import Path
from typing import Any

from maya.schemas import AuditEntry
from maya.utils import ensure_dir, stable_hash


class AuditLog:
    def __init__(self, path: Path | None = None, session_dir: Path | None = None):
        if session_dir is not None:
            self.path = session_dir / "audit.jsonl"
        elif path is not None:
            self.path = path
        else:
            raise ValueError("Either path or session_dir must be provided")
        ensure_dir(self.path.parent)
        self._last_hash = self._recover_last_hash()

    def _recover_last_hash(self) -> str | None:
        if not self.path.exists():
            return None
        last_line = None
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last_line = line
        if not last_line:
            return None
        payload = json.loads(last_line)
        return payload.get("entry_hash")

    def append_entry(
        self,
        *,
        agent_id: str,
        role: str,
        action_type: str,
        governance_layer: str,
        outcome: str,
        input_payload: Any,
        output_payload: Any,
        tool_used: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            agent_id=agent_id,
            role=role,
            action_type=action_type,
            tool_used=tool_used,
            input_hash=stable_hash(input_payload),
            output_hash=stable_hash(output_payload),
            governance_layer=governance_layer,
            outcome=outcome,
            details=details or {},
            previous_hash=self._last_hash,
        )
        serialized = entry.model_dump(mode="json")
        entry.entry_hash = stable_hash(serialized)
        self._last_hash = entry.entry_hash
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json() + "\n")
        return entry

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def entry_count(self) -> int:
        return len(self.entries())

    def export(self) -> list[dict[str, Any]]:
        return self.entries()

    def verify_chain(self) -> bool:
        previous_hash = None
        for entry in self.entries():
            if entry.get("previous_hash") != previous_hash:
                return False
            reconstructed = dict(entry)
            reconstructed["entry_hash"] = None
            expected_hash = stable_hash(reconstructed)
            if entry.get("entry_hash") != expected_hash:
                return False
            previous_hash = entry.get("entry_hash")
        return True

    def log(self, entry: AuditEntry) -> AuditEntry:
        entry.previous_hash = self._last_hash
        serialized = entry.model_dump(mode="json")
        entry.entry_hash = stable_hash(serialized)
        self._last_hash = entry.entry_hash
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json() + "\n")
        return entry


def audit_worker_main(request_queue: Queue, response_queue: Queue, audit_path: str) -> None:
    log = AuditLog(Path(audit_path))
    while True:
        request = request_queue.get()
        kind = request.get("kind")
        if kind == "close":
            response_queue.put({"kind": "closed"})
            return
        if kind == "append":
            entry = log.append_entry(
                agent_id=request["agent_id"],
                role=request["role"],
                action_type=request["action_type"],
                governance_layer=request["governance_layer"],
                outcome=request["outcome"],
                input_payload=request.get("input_payload"),
                output_payload=request.get("output_payload"),
                tool_used=request.get("tool_used"),
                details=request.get("details"),
            )
            response_queue.put({"kind": "append_result", "entry": entry.model_dump(mode="json")})
        elif kind == "entries":
            response_queue.put({"kind": "entries_result", "entries": log.entries()})


class AuditClient:
    def __init__(self, request_queue: Queue, response_queue: Queue):
        self.request_queue = request_queue
        self.response_queue = response_queue

    def append(self, **payload) -> dict[str, Any]:
        self.request_queue.put({"kind": "append", **payload})
        return self.response_queue.get()["entry"]

    def entries(self) -> list[dict[str, Any]]:
        self.request_queue.put({"kind": "entries"})
        return self.response_queue.get()["entries"]

    def close(self) -> None:
        self.request_queue.put({"kind": "close"})
        self.response_queue.get()


AuditLogger = AuditLog
