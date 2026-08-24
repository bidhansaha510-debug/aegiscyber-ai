from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseParser(ABC):
    PARSER_NAME: str = "base"
    SUPPORTED_TOOLS: list[str] = []

    @abstractmethod
    def parse(self, raw_output: str, tool_name: str = "", command: str = "") -> dict[str, Any]:
        ...

    def can_parse(self, tool_name: str) -> bool:
        return tool_name.lower() in [t.lower() for t in self.SUPPORTED_TOOLS]

    def _safe_extract(self, text: str, start_marker: str, end_marker: str) -> str:
        try:
            start = text.index(start_marker) + len(start_marker)
            end = text.index(end_marker, start)
            return text[start:end].strip()
        except ValueError:
            return ""

    def _extract_lines_matching(self, text: str, pattern: str) -> list[str]:
        import re
        return re.findall(pattern, text, re.MULTILINE)
