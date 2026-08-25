"""ATT&CK Navigator — exports ATT&CK Navigator layer JSON.

Generates JSON that can be imported into MITRE's ATT&CK Navigator
visualization tool (https://mitre-attack.github.io/attack-navigator/).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.mitre.attack_mapper import ATTACKMapper, TACTICS
from app.logging_config import get_logger

logger = get_logger("mitre.navigator")


class NavigatorTechnique(BaseModel):
    """A single technique in the navigator layer."""
    techniqueID: str
    tactic: str = ""
    color: str = ""
    comment: str = ""
    enabled: bool = True
    score: int = 0
    metadata: list[dict[str, str]] = Field(default_factory=list)


class NavigatorLayer(BaseModel):
    """An ATT&CK Navigator layer."""
    name: str = "AegisCyber AI - Investigation Coverage"
    versions: dict[str, str] = Field(default_factory=lambda: {
        "attack": "14",
        "navigator": "4.9.1",
        "layer": "4.5",
    })
    domain: str = "enterprise-attack"
    description: str = ""
    filters: dict[str, Any] = Field(default_factory=lambda: {
        "platforms": ["Linux", "Windows", "Network"],
    })
    sorting: int = 3
    layout: dict[str, Any] = Field(default_factory=lambda: {
        "layout": "side",
        "aggregateFunction": "average",
        "showID": True,
        "showName": True,
        "showAggregateScores": False,
        "countUnscored": False,
    })
    hideDisabled: bool = False
    techniques: list[NavigatorTechnique] = Field(default_factory=list)
    gradient: dict[str, Any] = Field(default_factory=lambda: {
        "colors": ["#ffffff", "#66b1ff", "#0d47a1"],
        "minValue": 0,
        "maxValue": 100,
    })
    legendItems: list[dict[str, str]] = Field(default_factory=lambda: [
        {"label": "Planned",   "color": "#ffeb3b"},
        {"label": "Executing", "color": "#ff9800"},
        {"label": "Completed", "color": "#4caf50"},
        {"label": "Blocked",   "color": "#f44336"},
    ])
    showTacticRowBackground: bool = True
    tacticRowBackground: str = "#205b8f"
    selectTechniquesAcrossTactics: bool = True
    selectSubtechniquesWithParent: bool = True
    selectVisibleTechniques: bool = False
    metadata: list[dict[str, str]] = Field(default_factory=list)


STATUS_COLORS = {
    "planned":   "#ffeb3b",
    "executing": "#ff9800",
    "completed": "#4caf50",
    "blocked":   "#f44336",
}


class ATTACKNavigator:
    """Generates ATT&CK Navigator layer JSON from mapper data."""

    def __init__(self, mapper: ATTACKMapper) -> None:
        self._mapper = mapper

    def generate_layer(
        self,
        name: str = "",
        description: str = "",
    ) -> NavigatorLayer:
        """Generate a Navigator layer from current ATT&CK mapper state."""
        layer = NavigatorLayer(
            name=name or "AegisCyber AI - Investigation Coverage",
            description=description or f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        )

        layer.metadata = [
            {"name": "generator", "value": "AegisCyber AI"},
            {"name": "generated_at", "value": datetime.now(timezone.utc).isoformat()},
        ]

        technique_statuses: dict[str, dict[str, Any]] = {}

        for phase in self._mapper.get_kill_chain_status():
            tactic_name = self._tactic_id_to_navigator_name(phase.tactic_id)

            for tech_id in phase.techniques_completed:
                key = f"{tech_id}|{tactic_name}"
                technique_statuses[key] = {
                    "id": tech_id,
                    "tactic": tactic_name,
                    "status": "completed",
                    "score": 100,
                }

            for tech_id in phase.techniques_executed:
                key = f"{tech_id}|{tactic_name}"
                if key not in technique_statuses:
                    technique_statuses[key] = {
                        "id": tech_id,
                        "tactic": tactic_name,
                        "status": "executing",
                        "score": 60,
                    }

            for tech_id in phase.techniques_planned:
                key = f"{tech_id}|{tactic_name}"
                if key not in technique_statuses:
                    technique_statuses[key] = {
                        "id": tech_id,
                        "tactic": tactic_name,
                        "status": "planned",
                        "score": 30,
                    }

            for tech_id in phase.techniques_blocked:
                key = f"{tech_id}|{tactic_name}"
                if key not in technique_statuses:
                    technique_statuses[key] = {
                        "id": tech_id,
                        "tactic": tactic_name,
                        "status": "blocked",
                        "score": 10,
                    }

        for key, data in technique_statuses.items():
            color = STATUS_COLORS.get(data["status"], "#ffffff")
            tools = self._find_tools_for_technique(data["id"])

            layer.techniques.append(NavigatorTechnique(
                techniqueID=data["id"],
                tactic=data["tactic"],
                color=color,
                comment=f"Status: {data['status']} | Tools: {', '.join(tools)}",
                score=data["score"],
                metadata=[
                    {"name": "status", "value": data["status"]},
                    {"name": "tools", "value": ", ".join(tools)},
                ],
            ))

        logger.info("Generated Navigator layer with %d techniques", len(layer.techniques))
        return layer

    def export_json(self, name: str = "", description: str = "") -> str:
        """Export Navigator layer as JSON string."""
        layer = self.generate_layer(name, description)
        return layer.model_dump_json(indent=2)

    def export_to_file(self, filepath: str, name: str = "", description: str = "") -> None:
        """Export Navigator layer to a JSON file."""
        json_str = self.export_json(name, description)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_str)
        logger.info("Navigator layer exported to %s", filepath)

    def _tactic_id_to_navigator_name(self, tactic_id: str) -> str:
        """Convert tactic ID to Navigator-compatible tactic name."""
        name_map = {
            "TA0043": "reconnaissance",
            "TA0042": "resource-development",
            "TA0001": "initial-access",
            "TA0002": "execution",
            "TA0003": "persistence",
            "TA0004": "privilege-escalation",
            "TA0005": "defense-evasion",
            "TA0006": "credential-access",
            "TA0007": "discovery",
            "TA0008": "lateral-movement",
            "TA0009": "collection",
            "TA0011": "command-and-control",
            "TA0010": "exfiltration",
            "TA0040": "impact",
        }
        return name_map.get(tactic_id, "")

    def _find_tools_for_technique(self, technique_id: str) -> list[str]:
        """Find tools that map to a specific technique."""
        from app.mitre.attack_mapper import TOOL_TECHNIQUE_MAP
        tools = []
        for tool_name, techs in TOOL_TECHNIQUE_MAP.items():
            if any(t["technique_id"] == technique_id for t in techs):
                tools.append(tool_name)
        return tools
