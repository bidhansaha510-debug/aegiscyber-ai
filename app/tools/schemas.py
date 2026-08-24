from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field

from app.config import ToolCategory, RiskLevel


class ArgumentType(str, enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    PORT = "port"
    PORT_RANGE = "port_range"
    IP_ADDRESS = "ip_address"
    IP_RANGE = "ip_range"
    DOMAIN = "domain"
    URL = "url"
    FILE_PATH = "file_path"
    WORDLIST = "wordlist"
    ENUM = "enum"


class ToolArgument(BaseModel):
    name: str
    flag: str
    description: str = ""
    arg_type: ArgumentType = ArgumentType.STRING
    required: bool = False
    default: Any = None
    choices: list[str] = Field(default_factory=list)
    dangerous: bool = False


class ToolCapability(BaseModel):
    name: str
    description: str = ""


class ToolExample(BaseModel):
    description: str
    command: str
    expected_output: str = ""
    risk_level: str = "LOW_RISK"


class OutputPattern(BaseModel):
    name: str
    pattern: str
    description: str = ""


class ToolDefinition(BaseModel):
    name: str
    description: str
    category: list[str] = Field(default_factory=list)
    binary: str
    execution_backend: list[str] = Field(default_factory=lambda: ["wsl2"])
    version: str = ""
    documentation: str = ""
    capabilities: list[str] = Field(default_factory=list)
    input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    arguments: list[ToolArgument] = Field(default_factory=list)
    required_arguments: list[str] = Field(default_factory=list)
    optional_arguments: list[str] = Field(default_factory=list)
    danger_level: str = "LOW_RISK"
    allowed_modes: list[str] = Field(default_factory=lambda: ["passive", "active"])
    examples: list[ToolExample] = Field(default_factory=list)
    expected_output_patterns: list[OutputPattern] = Field(default_factory=list)
    error_patterns: list[OutputPattern] = Field(default_factory=list)
    parser: str = "generic"
    default_timeout: int = 120
    requires_root: bool = False


class InstalledTool(BaseModel):
    name: str
    backend: str
    version: str = ""
    path: str = ""
    is_available: bool = False
    last_checked: str = ""
    success_count: int = 0
    failure_count: int = 0
    avg_execution_time: float = 0.0


class ToolScore(BaseModel):
    tool_name: str
    capability_match: float = 0.0
    input_match: float = 0.0
    output_match: float = 0.0
    reliability: float = 0.0
    installation_status: float = 0.0
    historical_success: float = 0.0
    risk_penalty: float = 0.0
    total_score: float = 0.0

    def calculate_total(self) -> float:
        self.total_score = (
            self.capability_match
            + self.input_match
            + self.output_match
            + self.reliability
            + self.installation_status
            + self.historical_success
            - self.risk_penalty
        )
        return self.total_score
