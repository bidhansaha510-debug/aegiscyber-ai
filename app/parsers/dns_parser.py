from __future__ import annotations

import re
from typing import Any

from app.parsers.base import BaseParser


class DNSParser(BaseParser):
    PARSER_NAME = "dns"
    SUPPORTED_TOOLS = ["dig", "nslookup", "host", "dnsx"]

    def parse(self, raw_output: str, tool_name: str = "", command: str = "") -> dict[str, Any]:
        if tool_name.lower() == "dig":
            return self._parse_dig(raw_output)
        if tool_name.lower() == "dnsx":
            return self._parse_dnsx(raw_output)
        if tool_name.lower() == "nslookup":
            return self._parse_nslookup(raw_output)
        if tool_name.lower() == "host":
            return self._parse_host(raw_output)
        return self._parse_generic_dns(raw_output)

    def _parse_dnsx(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"records": [], "format": "dnsx"}
        for line in output.split("\n"):
            line = line.strip()
            match = re.match(r"(\S+)\s+\[(\w+)\]\s+\[(.*)\]", line)
            if match:
                result["records"].append({
                    "name": match.group(1),
                    "type": match.group(2),
                    "value": match.group(3),
                })
        return result

    def _parse_dig(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"records": [], "query_info": {}, "format": "dig"}

        status_match = re.search(r"status:\s+(\w+)", output)
        if status_match:
            result["query_info"]["status"] = status_match.group(1)

        query_match = re.search(r"QUERY:\s+(\d+)", output)
        answer_match = re.search(r"ANSWER:\s+(\d+)", output)
        if query_match:
            result["query_info"]["query_count"] = int(query_match.group(1))
        if answer_match:
            result["query_info"]["answer_count"] = int(answer_match.group(1))

        in_answer = False
        for line in output.split("\n"):
            line = line.strip()
            if ";; ANSWER SECTION:" in line:
                in_answer = True
                continue
            if in_answer and line.startswith(";;"):
                in_answer = False
                continue
            if in_answer and line and not line.startswith(";"):
                parts = line.split()
                if len(parts) >= 5:
                    result["records"].append({
                        "name": parts[0],
                        "ttl": int(parts[1]) if parts[1].isdigit() else 0,
                        "class": parts[2],
                        "type": parts[3],
                        "value": " ".join(parts[4:]),
                    })

        server_match = re.search(r"SERVER:\s+(.+?)#", output)
        if server_match:
            result["query_info"]["server"] = server_match.group(1).strip()

        time_match = re.search(r"Query time:\s+(\d+)\s+msec", output)
        if time_match:
            result["query_info"]["query_time_ms"] = int(time_match.group(1))

        return result

    def _parse_nslookup(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"records": [], "server": "", "format": "nslookup"}

        server_match = re.search(r"Server:\s+(.+)", output)
        if server_match:
            result["server"] = server_match.group(1).strip()

        for line in output.split("\n"):
            line = line.strip()
            addr_match = re.match(r"Address:\s+(.+)", line)
            if addr_match:
                addr = addr_match.group(1).strip()
                if addr != result["server"] and "#" not in addr:
                    result["records"].append({
                        "type": "A",
                        "value": addr,
                    })

            name_match = re.match(r"Name:\s+(.+)", line)
            if name_match:
                result["records"].append({
                    "type": "PTR",
                    "value": name_match.group(1).strip(),
                })

        return result

    def _parse_host(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"records": [], "format": "host"}

        for line in output.split("\n"):
            line = line.strip()
            if " has address " in line:
                parts = line.split(" has address ")
                result["records"].append({
                    "name": parts[0].strip(),
                    "type": "A",
                    "value": parts[1].strip(),
                })
            elif " has IPv6 address " in line:
                parts = line.split(" has IPv6 address ")
                result["records"].append({
                    "name": parts[0].strip(),
                    "type": "AAAA",
                    "value": parts[1].strip(),
                })
            elif " mail is handled by " in line:
                parts = line.split(" mail is handled by ")
                result["records"].append({
                    "name": parts[0].strip(),
                    "type": "MX",
                    "value": parts[1].strip(),
                })
            elif " name server " in line:
                parts = line.split(" name server ")
                result["records"].append({
                    "name": parts[0].strip(),
                    "type": "NS",
                    "value": parts[1].strip(),
                })

        return result

    def _parse_generic_dns(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"records": [], "format": "generic"}
        ip_pattern = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")
        for line in output.split("\n"):
            ips = ip_pattern.findall(line.strip())
            for ip in ips:
                result["records"].append({"type": "A", "value": ip, "raw_line": line.strip()})
        return result
