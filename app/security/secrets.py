from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.logging_config import get_logger

logger = get_logger("security.secrets")


class SecretsManager:
    def __init__(self, secrets_dir: str | Path = "data/secrets") -> None:
        self._secrets_dir = Path(secrets_dir)
        self._secrets_dir.mkdir(parents=True, exist_ok=True)
        self._key_file = self._secrets_dir / ".keyfile"
        self._secrets_file = self._secrets_dir / "vault.enc"
        self._fernet: Fernet | None = None
        self._cache: dict[str, str] = {}
        self._initialize_encryption()

    def _initialize_encryption(self) -> None:
        if self._key_file.exists():
            key = self._key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self._key_file.write_bytes(key)
            if os.name == "nt":
                import subprocess
                subprocess.run(
                    ["attrib", "+H", str(self._key_file)],
                    capture_output=True,
                    check=False,
                )
        self._fernet = Fernet(key)
        self._load_vault()

    def _load_vault(self) -> None:
        if not self._secrets_file.exists():
            self._cache = {}
            return
        try:
            encrypted_data = self._secrets_file.read_bytes()
            decrypted = self._fernet.decrypt(encrypted_data)
            import orjson
            self._cache = orjson.loads(decrypted)
        except Exception as e:
            logger.error("Failed to load secrets vault: %s", e)
            self._cache = {}

    def _save_vault(self) -> None:
        try:
            import orjson
            data = orjson.dumps(self._cache)
            encrypted = self._fernet.encrypt(data)
            self._secrets_file.write_bytes(encrypted)
        except Exception as e:
            logger.error("Failed to save secrets vault: %s", e)

    def set_secret(self, key: str, value: str) -> None:
        self._cache[key] = value
        self._save_vault()
        logger.info("Secret stored: %s", key)

    def get_secret(self, key: str) -> str | None:
        return self._cache.get(key)

    def delete_secret(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            self._save_vault()
            logger.info("Secret deleted: %s", key)
            return True
        return False

    def list_keys(self) -> list[str]:
        return list(self._cache.keys())

    def has_secret(self, key: str) -> bool:
        return key in self._cache

    def clear_all(self) -> None:
        self._cache.clear()
        self._save_vault()
        logger.info("All secrets cleared")
