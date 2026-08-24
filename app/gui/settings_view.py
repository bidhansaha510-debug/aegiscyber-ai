from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QSpinBox, QFormLayout,
)
from PySide6.QtCore import Qt, Signal

from app.gui.theme import COLORS


class SettingsPage(QWidget):
    settings_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("⚙ Settings")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLORS['text_bright']};"
        )
        layout.addWidget(title)

        ollama_group = QGroupBox("Ollama Configuration")
        ollama_layout = QFormLayout(ollama_group)
        ollama_layout.setSpacing(8)

        self._ollama_host = QLineEdit("http://localhost:11434")
        ollama_layout.addRow("Host:", self._ollama_host)

        self._ollama_model = QLineEdit("llama3:latest")
        ollama_layout.addRow("Model:", self._ollama_model)

        self._ollama_temp = QLineEdit("0.1")
        ollama_layout.addRow("Temperature:", self._ollama_temp)

        self._ollama_tokens = QSpinBox()
        self._ollama_tokens.setRange(256, 32768)
        self._ollama_tokens.setValue(4096)
        ollama_layout.addRow("Max Tokens:", self._ollama_tokens)

        layout.addWidget(ollama_group)

        security_group = QGroupBox("Security Policy")
        security_layout = QFormLayout(security_group)
        security_layout.setSpacing(8)

        self._auto_approve_safe = QCheckBox()
        self._auto_approve_safe.setChecked(True)
        security_layout.addRow("Auto-approve SAFE:", self._auto_approve_safe)

        self._auto_approve_low = QCheckBox()
        self._auto_approve_low.setChecked(True)
        security_layout.addRow("Auto-approve LOW_RISK:", self._auto_approve_low)

        self._require_medium = QCheckBox()
        self._require_medium.setChecked(True)
        security_layout.addRow("Require approval MEDIUM:", self._require_medium)

        self._require_high = QCheckBox()
        self._require_high.setChecked(True)
        security_layout.addRow("Require approval HIGH:", self._require_high)

        self._block_high = QCheckBox()
        self._block_high.setChecked(False)
        security_layout.addRow("Block HIGH_RISK:", self._block_high)

        self._max_concurrent = QSpinBox()
        self._max_concurrent.setRange(1, 20)
        self._max_concurrent.setValue(5)
        security_layout.addRow("Max Concurrent:", self._max_concurrent)

        layout.addWidget(security_group)

        exec_group = QGroupBox("Execution Backends")
        exec_layout = QFormLayout(exec_group)

        self._enable_wsl = QCheckBox()
        self._enable_wsl.setChecked(True)
        exec_layout.addRow("Enable WSL2:", self._enable_wsl)

        self._enable_docker = QCheckBox()
        self._enable_docker.setChecked(True)
        exec_layout.addRow("Enable Docker:", self._enable_docker)

        self._default_timeout = QSpinBox()
        self._default_timeout.setRange(10, 3600)
        self._default_timeout.setValue(120)
        exec_layout.addRow("Default Timeout (s):", self._default_timeout)

        layout.addWidget(exec_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("💾 Save Settings")
        save_btn.setObjectName("primaryButton")
        save_btn.setMinimumWidth(160)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _save(self) -> None:
        settings = {
            "ollama_host": self._ollama_host.text(),
            "ollama_model": self._ollama_model.text(),
            "ollama_temperature": float(self._ollama_temp.text() or "0.1"),
            "ollama_max_tokens": self._ollama_tokens.value(),
            "auto_approve_safe": self._auto_approve_safe.isChecked(),
            "auto_approve_low": self._auto_approve_low.isChecked(),
            "require_medium": self._require_medium.isChecked(),
            "require_high": self._require_high.isChecked(),
            "block_high": self._block_high.isChecked(),
            "max_concurrent": self._max_concurrent.value(),
            "enable_wsl": self._enable_wsl.isChecked(),
            "enable_docker": self._enable_docker.isChecked(),
            "default_timeout": self._default_timeout.value(),
        }
        self.settings_changed.emit(settings)

    def load_settings(self, settings: dict) -> None:
        self._ollama_host.setText(settings.get("ollama_host", "http://localhost:11434"))
        self._ollama_model.setText(settings.get("ollama_model", "llama3:latest"))
        self._ollama_temp.setText(str(settings.get("ollama_temperature", 0.1)))
        self._ollama_tokens.setValue(settings.get("ollama_max_tokens", 4096))
        self._auto_approve_safe.setChecked(settings.get("auto_approve_safe", True))
        self._auto_approve_low.setChecked(settings.get("auto_approve_low", True))
        self._require_medium.setChecked(settings.get("require_medium", True))
        self._require_high.setChecked(settings.get("require_high", True))
        self._block_high.setChecked(settings.get("block_high", False))
        self._max_concurrent.setValue(settings.get("max_concurrent", 5))
        self._enable_wsl.setChecked(settings.get("enable_wsl", True))
        self._enable_docker.setChecked(settings.get("enable_docker", True))
        self._default_timeout.setValue(settings.get("default_timeout", 120))
