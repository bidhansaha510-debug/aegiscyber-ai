from __future__ import annotations

import re
from typing import Any

from app.parsers.base import BaseParser


class WhoisParser(BaseParser):
    PARSER_NAME = "whois"
    SUPPORTED_TOOLS = ["whois"]

    def parse(self, raw_output: str, tool_name: str = "", command: str = "") -> dict[str, Any]:
        result: dict[str, Any] = {
            "domain": "",
            "registrar": "",
            "creation_date": "",
            "expiration_date": "",
            "updated_date": "",
            "status": [],
            "name_servers": [],
            "registrant": {},
            "admin_contact": {},
            "tech_contact": {},
            "raw_fields": {},
            "format": "whois",
        }

        field_mapping = {
            "domain name": "domain",
            "registrar": "registrar",
            "creation date": "creation_date",
            "created": "creation_date",
            "registry expiry date": "expiration_date",
            "expiration date": "expiration_date",
            "expires": "expiration_date",
            "updated date": "updated_date",
            "last updated": "updated_date",
        }

        for line in raw_output.split("\n"):
            line = line.strip()
            if not line or line.startswith("%") or line.startswith("#"):
                continue

            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()

                if not value:
                    continue

                mapped = field_mapping.get(key)
                if mapped:
                    result[mapped] = value
                elif "name server" in key:
                    result["name_servers"].append(value)
                elif "status" in key:
                    result["status"].append(value)
                elif "registrant" in key:
                    sub_key = key.replace("registrant", "").strip()
                    if sub_key:
                        result["registrant"][sub_key] = value
                    else:
                        result["registrant"]["name"] = value
                elif "admin" in key:
                    sub_key = key.replace("admin", "").strip()
                    result["admin_contact"][sub_key if sub_key else "name"] = value
                elif "tech" in key:
                    sub_key = key.replace("tech", "").strip()
                    result["tech_contact"][sub_key if sub_key else "name"] = value
                else:
                    result["raw_fields"][key] = value

        return result
