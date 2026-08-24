from __future__ import annotations

from typing import Any

from app.parsers.base import BaseParser
from app.parsers.nmap_parser import NmapParser
from app.parsers.dns_parser import DNSParser
from app.parsers.whois_parser import WhoisParser
from app.parsers.http_parser import HTTPParser
from app.parsers.generic_parser import GenericParser
from app.logging_config import get_logger

logger = get_logger("parsers.registry")


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {}
        self._tool_parser_map: dict[str, str] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(NmapParser())
        self.register(DNSParser())
        self.register(WhoisParser())
        self.register(HTTPParser())
        self.register(GenericParser())

    def register(self, parser: BaseParser) -> None:
        self._parsers[parser.PARSER_NAME] = parser
        for tool in parser.SUPPORTED_TOOLS:
            self._tool_parser_map[tool.lower()] = parser.PARSER_NAME
        logger.debug("Parser registered: %s (tools: %s)", parser.PARSER_NAME, parser.SUPPORTED_TOOLS)

    def get_parser(self, parser_name: str) -> BaseParser | None:
        return self._parsers.get(parser_name)

    def get_parser_for_tool(self, tool_name: str) -> BaseParser:
        parser_name = self._tool_parser_map.get(tool_name.lower(), "generic")
        return self._parsers.get(parser_name, self._parsers["generic"])

    def parse_output(self, raw_output: str, tool_name: str = "", command: str = "") -> dict[str, Any]:
        parser = self.get_parser_for_tool(tool_name)
        try:
            result = parser.parse(raw_output, tool_name, command)
            result["_parser"] = parser.PARSER_NAME
            result["_tool"] = tool_name
            return result
        except Exception as e:
            logger.error("Parser %s failed for tool %s: %s", parser.PARSER_NAME, tool_name, e)
            generic = self._parsers["generic"]
            result = generic.parse(raw_output, tool_name, command)
            result["_parser"] = "generic"
            result["_parser_fallback"] = True
            result["_original_parser_error"] = str(e)
            return result

    def list_parsers(self) -> list[str]:
        return list(self._parsers.keys())

    def list_supported_tools(self) -> dict[str, str]:
        return dict(self._tool_parser_map)
