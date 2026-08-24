from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from app.parsers.base import BaseParser


class NmapParser(BaseParser):
    PARSER_NAME = "nmap"
    SUPPORTED_TOOLS = ["nmap"]

    def parse(self, raw_output: str, tool_name: str = "", command: str = "") -> dict[str, Any]:
        if raw_output.strip().startswith("<?xml"):
            return self._parse_xml(raw_output)
        if "Host:" in raw_output and "Ports:" in raw_output:
            return self._parse_greppable(raw_output)
        return self._parse_normal(raw_output)

    def _parse_xml(self, xml_output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"hosts": [], "scan_info": {}, "format": "xml"}
        try:
            root = ET.fromstring(xml_output)
            result["scan_info"] = {
                "scanner": root.get("scanner", "nmap"),
                "args": root.get("args", ""),
                "start_time": root.get("startstr", ""),
            }
            for host_elem in root.findall(".//host"):
                host: dict[str, Any] = {"ip": "", "hostname": "", "status": "", "ports": [], "os": []}

                addr = host_elem.find("address")
                if addr is not None:
                    host["ip"] = addr.get("addr", "")

                hostnames = host_elem.find("hostnames")
                if hostnames is not None:
                    hostname = hostnames.find("hostname")
                    if hostname is not None:
                        host["hostname"] = hostname.get("name", "")

                status = host_elem.find("status")
                if status is not None:
                    host["status"] = status.get("state", "")

                ports = host_elem.find("ports")
                if ports is not None:
                    for port_elem in ports.findall("port"):
                        port_info: dict[str, Any] = {
                            "port": int(port_elem.get("portid", 0)),
                            "protocol": port_elem.get("protocol", "tcp"),
                            "state": "",
                            "service": "",
                            "version": "",
                            "product": "",
                        }
                        state = port_elem.find("state")
                        if state is not None:
                            port_info["state"] = state.get("state", "")

                        service = port_elem.find("service")
                        if service is not None:
                            port_info["service"] = service.get("name", "")
                            port_info["product"] = service.get("product", "")
                            port_info["version"] = service.get("version", "")

                        host["ports"].append(port_info)

                os_elem = host_elem.find("os")
                if os_elem is not None:
                    for osmatch in os_elem.findall("osmatch"):
                        host["os"].append({
                            "name": osmatch.get("name", ""),
                            "accuracy": osmatch.get("accuracy", ""),
                        })

                result["hosts"].append(host)
        except ET.ParseError as e:
            result["parse_error"] = str(e)
        return result

    def _parse_greppable(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"hosts": [], "format": "greppable"}
        for line in output.strip().split("\n"):
            if not line.startswith("Host:"):
                continue
            host: dict[str, Any] = {"ip": "", "hostname": "", "ports": []}
            parts = line.split("\t")
            if parts:
                host_match = re.match(r"Host:\s+(\S+)\s*\(([^)]*)\)", parts[0])
                if host_match:
                    host["ip"] = host_match.group(1)
                    host["hostname"] = host_match.group(2)

            for part in parts:
                if part.startswith("Ports:"):
                    port_entries = part[6:].strip().split(",")
                    for entry in port_entries:
                        entry = entry.strip()
                        fields = entry.split("/")
                        if len(fields) >= 5:
                            host["ports"].append({
                                "port": int(fields[0]) if fields[0].isdigit() else 0,
                                "state": fields[1],
                                "protocol": fields[2],
                                "service": fields[4],
                                "version": fields[6] if len(fields) > 6 else "",
                            })
            if host["ip"]:
                result["hosts"].append(host)
        return result

    def _parse_normal(self, output: str) -> dict[str, Any]:
        result: dict[str, Any] = {"hosts": [], "format": "normal", "raw_summary": ""}
        current_host: dict[str, Any] | None = None

        for line in output.strip().split("\n"):
            line = line.strip()

            host_match = re.match(r"Nmap scan report for\s+(.+)", line)
            if host_match:
                if current_host:
                    result["hosts"].append(current_host)
                target = host_match.group(1)
                ip_match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", target)
                current_host = {
                    "ip": ip_match.group(1) if ip_match else target,
                    "hostname": target.split("(")[0].strip() if "(" in target else "",
                    "ports": [],
                }
                continue

            port_match = re.match(
                r"(\d+)/(tcp|udp)\s+(open|closed|filtered)\s+(\S+)\s*(.*)", line
            )
            if port_match and current_host:
                current_host["ports"].append({
                    "port": int(port_match.group(1)),
                    "protocol": port_match.group(2),
                    "state": port_match.group(3),
                    "service": port_match.group(4),
                    "version": port_match.group(5).strip(),
                })

        if current_host:
            result["hosts"].append(current_host)

        summary_lines = [l for l in output.split("\n") if "Nmap done" in l]
        if summary_lines:
            result["raw_summary"] = summary_lines[-1].strip()

        return result
