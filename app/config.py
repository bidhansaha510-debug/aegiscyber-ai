from __future__ import annotations

import enum
import os
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionBackendType(str, enum.Enum):
    NATIVE = "native"
    WSL2 = "wsl2"
    DOCKER = "docker"
    REMOTE = "remote"


class RiskLevel(str, enum.Enum):
    SAFE = "SAFE"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    BLOCKED = "BLOCKED"


class ToolCategory(str, enum.Enum):
    NETWORK_RECON = "NETWORK_RECON"
    WEB_RECON = "WEB_RECON"
    DNS = "DNS"
    SUBDOMAIN_DISCOVERY = "SUBDOMAIN_DISCOVERY"
    PORT_SCANNING = "PORT_SCANNING"
    SERVICE_ENUMERATION = "SERVICE_ENUMERATION"
    TLS_ANALYSIS = "TLS_ANALYSIS"
    OSINT = "OSINT"
    EMAIL_OSINT = "EMAIL_OSINT"
    USERNAME_OSINT = "USERNAME_OSINT"
    DOMAIN_OSINT = "DOMAIN_OSINT"
    IP_OSINT = "IP_OSINT"
    DOCUMENT_OSINT = "DOCUMENT_OSINT"
    METADATA_ANALYSIS = "METADATA_ANALYSIS"
    PACKET_ANALYSIS = "PACKET_ANALYSIS"
    VULNERABILITY_ASSESSMENT = "VULNERABILITY_ASSESSMENT"
    PASSWORD_AUDITING = "PASSWORD_AUDITING"
    WIRELESS_SECURITY = "WIRELESS_SECURITY"
    FORENSICS = "FORENSICS"
    REVERSE_ENGINEERING = "REVERSE_ENGINEERING"
    CTF = "CTF"
    LINUX_ADMINISTRATION = "LINUX_ADMINISTRATION"
    CRYPTOGRAPHY = "CRYPTOGRAPHY"
    UTILITY = "UTILITY"
    LOLBIN_RECON = "LOLBIN_RECON"
    LOLBIN_EXECUTION = "LOLBIN_EXECUTION"
    LOLBIN_EXFILTRATION = "LOLBIN_EXFILTRATION"
    LOLBIN_PERSISTENCE = "LOLBIN_PERSISTENCE"
    STEALTH_SCANNING = "STEALTH_SCANNING"
    LATERAL_MOVEMENT = "LATERAL_MOVEMENT"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"


class OllamaConfig(BaseSettings):
    host: str = "http://localhost:11434"
    model: str = "llama3:latest"
    embedding_model: str = "nomic-embed-text"
    timeout: int = 120
    max_tokens: int = 4096
    temperature: float = 0.1


class ExecutionConfig(BaseSettings):
    default_timeout: int = 300
    max_concurrent_executions: int = 5
    wsl_distro: str = "kali-linux"
    docker_image: str = "kalilinux/kali-rolling"
    enable_wsl: bool = True
    enable_docker: bool = True
    auto_start_docker: bool = True
    enable_native: bool = True
    max_output_size_bytes: int = 10 * 1024 * 1024


class SecurityConfig(BaseSettings):
    require_scope_confirmation: bool = True
    auto_approve_safe: bool = True
    auto_approve_low_risk: bool = False
    block_high_risk: bool = False
    require_approval_medium: bool = True
    require_approval_high: bool = True
    allowed_networks: list[str] = Field(default_factory=lambda: ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8"])
    blocked_executables: list[str] = Field(default_factory=lambda: ["rm", "mkfs", "dd", "shutdown", "reboot", "init"])
    audit_log_path: str = "logs/audit.jsonl"
    max_audit_file_size_mb: int = 100


class StealthConfig(BaseSettings):
    """Configuration for APT stealth / OPSEC-aware operations."""
    stealth_mode_default: bool = False
    opsec_threshold: int = 70
    traffic_profile: str = "careful"
    default_jitter_min: float = 2.0
    default_jitter_max: float = 15.0
    max_requests_per_minute: int = 10
    apply_evasion_flags: bool = True
    evasion_level: str = "careful"
    prefer_lolbins: bool = True
    enable_mitre_tracking: bool = True
    fragment_large_scans: bool = True
    respect_business_hours: bool = True


class ModelConfig(BaseSettings):
    specialized_model_path: str = "models/cyber_specialist"
    embedding_dimension: int = 768
    use_gpu: bool = True
    gpu_device: str = "cuda:0"
    lora_rank: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    training_batch_size: int = 4
    training_epochs: int = 3
    training_learning_rate: float = 2e-4


class DatabaseConfig(BaseSettings):
    db_path: str = "data/aegiscyber.db"
    echo_sql: bool = False


class APIConfig(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8741
    enable_api: bool = True
    api_key: str = ""


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    app_name: str = "AegisCyber AI"
    version: str = "1.0.0"
    debug: bool = False
    data_dir: Path = Field(default_factory=lambda: Path("data"))
    log_dir: Path = Field(default_factory=lambda: Path("logs"))
    tool_registry_dir: Path = Field(default_factory=lambda: Path("tool_registry"))
    config_dir: Path = Field(default_factory=lambda: Path("configs"))

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    stealth: StealthConfig = Field(default_factory=StealthConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: APIConfig = Field(default_factory=APIConfig)

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.tool_registry_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        Path(self.security.audit_log_path).parent.mkdir(parents=True, exist_ok=True)


_config_instance: AppConfig | None = None


def get_config() -> AppConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
        _config_instance.ensure_directories()
    return _config_instance


def reset_config() -> None:
    global _config_instance
    _config_instance = None
