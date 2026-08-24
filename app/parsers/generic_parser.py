from __future__ import annotations

import json
import re
from typing import Any

from app.parsers.base import BaseParser


class GenericParser(BaseParser):
    PARSER_NAME = "generic"
    SUPPORTED_TOOLS = []

    def parse(self, raw_output: str, tool_name: str = "", command: str = "") -> dict[str, Any]:
        if self._looks_like_json(raw_output):
            return self._parse_json(raw_output)
        if self._looks_like_csv(raw_output):
            return self._parse_csv(raw_output)
        return self._parse_text(raw_output)

    def _looks_like_json(self, text: str) -> bool:
        stripped = text.strip()
        return (stripped.startswith("{") and stripped.endswith("}")) or \
               (stripped.startswith("[") and stripped.endswith("]"))

    def _looks_like_csv(self, text: str) -> bool:
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return False
        first_line_commas = lines[0].count(",")
        if first_line_commas < 1:
            return False
        return all(abs(line.count(",") - first_line_commas) <= 1 for line in lines[:5])

    def _parse_json(self, text: str) -> dict[str, Any]:
        try:
            data = json.loads(text.strip())
            if isinstance(data, list):
                return {"items": data, "count": len(data), "format": "json"}
            if isinstance(data, dict):
                data["format"] = "json"
                return data
            return {"data": data, "format": "json"}
        except json.JSONDecodeError:
            return self._parse_text(text)

    def _parse_csv(self, text: str) -> dict[str, Any]:
        lines = text.strip().split("\n")
        headers = [h.strip().strip('"') for h in lines[0].split(",")]
        rows = []
        for line in lines[1:]:
            values = [v.strip().strip('"') for v in line.split(",")]
            row = {}
            for i, header in enumerate(headers):
                row[header] = values[i] if i < len(values) else ""
            rows.append(row)
        return {"headers": headers, "rows": rows, "count": len(rows), "format": "csv"}

    def _parse_text(self, text: str) -> dict[str, Any]:
        lines = text.strip().split("\n")
        result: dict[str, Any] = {
            "line_count": len(lines),
            "format": "text",
            "content": text[:10000],
        }

        ips = set(re.findall(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", text))
        if ips:
            result["extracted_ips"] = sorted(ips)

        domains = set(re.findall(
            r"\b([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z]{2,})+)\b",
            text,
        ))
        if domains:
            result["extracted_domains"] = sorted(domains)

        urls = set(re.findall(r"https?://[^\s<>\"']+", text))
        if urls:
            result["extracted_urls"] = sorted(urls)

        emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))
        if emails:
            result["extracted_emails"] = sorted(emails)

        ports = set(re.findall(r"\b(\d{1,5})/(tcp|udp)\b", text))
        if ports:
            result["extracted_ports"] = [{"port": int(p), "protocol": proto} for p, proto in ports]

        return result
