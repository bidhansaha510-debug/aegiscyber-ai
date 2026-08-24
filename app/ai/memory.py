from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.database.connection import DatabaseManager
from app.logging_config import get_logger

logger = get_logger("ai.memory")


class ConversationMemory:
    def __init__(self, session_id: str | None = None) -> None:
        self._session_id = session_id or str(uuid.uuid4())[:12]
        self._messages: list[dict[str, str]] = []
        self._max_messages = 50

    @property
    def session_id(self) -> str:
        return self._session_id

    def add_message(self, role: str, content: str) -> None:
        self._messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

    def get_messages(self, limit: int = 20) -> list[dict[str, str]]:
        return self._messages[-limit:]

    def get_chat_messages(self, limit: int = 20) -> list[dict[str, str]]:
        return [{"role": m["role"], "content": m["content"]} for m in self._messages[-limit:]]

    def get_context_summary(self, limit: int = 10) -> str:
        if not self._messages:
            return "No previous conversation"
        recent = self._messages[-limit:]
        return "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in recent)

    def clear(self) -> None:
        self._messages.clear()


class InvestigationMemory:
    def __init__(self, investigation_id: str) -> None:
        self._investigation_id = investigation_id
        self._facts: list[dict[str, Any]] = []
        self._findings: list[dict[str, Any]] = []
        self._targets: set[str] = set()

    @property
    def investigation_id(self) -> str:
        return self._investigation_id

    def add_fact(self, fact_type: str, value: str, source: str = "", confidence: float = 0.0) -> None:
        self._facts.append({
            "type": fact_type,
            "value": value,
            "source": source,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def add_finding(self, tool: str, finding: dict[str, Any]) -> None:
        self._findings.append({
            "tool": tool,
            "finding": finding,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def add_target(self, target: str) -> None:
        self._targets.add(target)

    def get_facts(self, fact_type: str | None = None) -> list[dict[str, Any]]:
        if fact_type:
            return [f for f in self._facts if f["type"] == fact_type]
        return self._facts

    def get_findings(self) -> list[dict[str, Any]]:
        return self._findings

    def get_facts_summary(self) -> str:
        if not self._facts:
            return "No facts discovered yet"
        lines = []
        for fact in self._facts:
            lines.append(f"[{fact['type']}] {fact['value']} (source: {fact['source']}, confidence: {fact['confidence']})")
        return "\n".join(lines)

    def get_targets(self) -> set[str]:
        return self._targets


class ToolMemory:
    def __init__(self) -> None:
        self._history: dict[str, list[dict[str, Any]]] = {}

    def record_execution(self, tool_name: str, success: bool, duration: float, target: str = "") -> None:
        if tool_name not in self._history:
            self._history[tool_name] = []
        self._history[tool_name].append({
            "success": success,
            "duration": duration,
            "target": target,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_success_rate(self, tool_name: str) -> float:
        history = self._history.get(tool_name, [])
        if not history:
            return 0.0
        successes = sum(1 for h in history if h["success"])
        return successes / len(history)

    def get_avg_duration(self, tool_name: str) -> float:
        history = self._history.get(tool_name, [])
        if not history:
            return 0.0
        return sum(h["duration"] for h in history) / len(history)

    def get_history(self, tool_name: str) -> list[dict[str, Any]]:
        return self._history.get(tool_name, [])


class MemoryManager:
    def __init__(self) -> None:
        self._conversation = ConversationMemory()
        self._investigations: dict[str, InvestigationMemory] = {}
        self._tool_memory = ToolMemory()
        self._db: DatabaseManager | None = None

    @property
    def conversation(self) -> ConversationMemory:
        return self._conversation

    @property
    def tool_memory(self) -> ToolMemory:
        return self._tool_memory

    def set_database(self, db: DatabaseManager) -> None:
        self._db = db

    def new_session(self) -> None:
        self._conversation = ConversationMemory()

    def create_investigation(self, investigation_id: str) -> InvestigationMemory:
        memory = InvestigationMemory(investigation_id)
        self._investigations[investigation_id] = memory
        return memory

    def get_investigation(self, investigation_id: str) -> InvestigationMemory:
        if investigation_id not in self._investigations:
            self._investigations[investigation_id] = InvestigationMemory(investigation_id)
        return self._investigations[investigation_id]

    def get_or_create_investigation(self, investigation_id: str) -> InvestigationMemory:
        if investigation_id not in self._investigations:
            self._investigations[investigation_id] = InvestigationMemory(investigation_id)
        return self._investigations[investigation_id]

    async def persist_conversation(self) -> None:
        if not self._db:
            return
        for msg in self._conversation.get_messages():
            await self._db.execute(
                "INSERT INTO memory_conversation (session_id, role, content) VALUES (?, ?, ?)",
                (self._conversation.session_id, msg["role"], msg["content"]),
            )

    async def persist_investigation(self, investigation_id: str) -> None:
        if not self._db:
            return
        memory = self._investigations.get(investigation_id)
        if not memory:
            return
        for fact in memory.get_facts():
            await self._db.execute(
                "INSERT INTO memory_investigation (investigation_id, fact_type, fact_value, evidence_source, confidence) VALUES (?, ?, ?, ?, ?)",
                (investigation_id, fact["type"], fact["value"], fact.get("source", ""), fact.get("confidence", 0.0)),
            )
