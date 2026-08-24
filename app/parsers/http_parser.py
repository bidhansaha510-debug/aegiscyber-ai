from __future__ import annotations

import re
from typing import Any

from app.parsers.base import BaseParser


class HTTPParser(BaseParser):
    PARSER_NAME = "http"
    SUPPORTED_TOOLS = ["curl", "httpx", "wget"]

    def parse(self, raw_output: str, tool_name: str = "", command: str = "") -> dict[str, Any]:
        if tool_name.lower() == "httpx":
            return self._parse_httpx(raw_output)
        if "-I" in (command or "") or "-v" in (command or ""):
            return self._parse_headers(raw_output)
        return self._parse_generic_http(raw_output)

    def _parse_headers(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status_code": 0,
            "status_text": "",
            "headers": {},
            "technologies": [],
            "format": "headers",
        }

        lines = output.strip().split("\n")
        for line in lines:
            line = line.strip()
            status_match = re.match(r"HTTP/[\d.]+\s+(\d+)\s*(.*)", line)
            if status_match:
                result["status_code"] = int(status_match.group(1))
                result["status_text"] = status_match.group(2).strip()
                continue

            if ":" in line and not line.startswith("<") and not line.startswith(">"):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if key and value:
                    result["headers"][key.lower()] = value

        if "server" in result["headers"]:
            result["technologies"].append(result["headers"]["server"])
        if "x-powered-by" in result["headers"]:
            result["technologies"].append(result["headers"]["x-powered-by"])

        return result

    def _parse_httpx(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"urls": [], "format": "httpx"}

        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            entry: dict[str, Any] = {"url": "", "status_code": 0, "title": "", "technologies": []}

            url_match = re.match(r"(https?://\S+)", line)
            if url_match:
                entry["url"] = url_match.group(1)

            status_match = re.search(r"\[(\d{3})\]", line)
            if status_match:
                entry["status_code"] = int(status_match.group(1))

            title_match = re.search(r"\[(.+?)\]", line)
            if title_match and not status_match:
                entry["title"] = title_match.group(1)

            tech_match = re.findall(r"\[([^\]]+)\]", line)
            for t in tech_match:
                if not t.isdigit() and len(t) > 2:
                    entry["technologies"].append(t)

            if entry["url"]:
                result["urls"].append(entry)

        return result

    def _parse_generic_http(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"content_length": len(output), "format": "generic_http"}
        urls = re.findall(r"https?://[^\s<>\"']+", output)
        result["extracted_urls"] = list(set(urls))
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", output)
        result["extracted_emails"] = list(set(emails))
        return result
