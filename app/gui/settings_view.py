from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QSpinBox, QFormLayout,
)
from PySide6.QtCore import Qt, Signal

from app.gui.theme import COLORS, FONT_SANS, FONT_MONO


def _section_card(title: str) -> tuple[QFrame, QFormLayout]:
    """Create a raised card frame with a title and form layout."""
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background-color: {COLORS['bg_surface_raised']}; "
        f"border: 1px solid {COLORS['border_hairline']}; border-radius: 8px; }}"
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(8)

    heading = QLabel(title)
    heading.setStyleSheet(
        f"color: {COLORS['text_primary']}; font-family: {FONT_SANS}; "
        f"font-size: 14px; font-weight: 600; background: transparent; "
        f"border: none;"
    )
    layout.addWidget(heading)

    form = QFormLayout()
    form.setSpacing(8)
    form.setContentsMargins(0, 8, 0, 0)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    layout.addLayout(form)

    return card, form


def _toggle(checked: bool = False) -> QCheckBox:
    """Create a toggle switch (custom QSS via objectName)."""
    cb = QCheckBox()
    cb.setObjectName("toggleSwitch")
    cb.setChecked(checked)
    return cb


class SettingsPage(QWidget):
    settings_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLORS['text_primary']}; "
            f"font-family: {FONT_SANS};"
        )
        layout.addWidget(title)

        # ── Ollama Configuration ──
        ollama_card, ollama_form = _section_card("Ollama Configuration")

        self._ollama_host = QLineEdit("http://localhost:11434")
        ollama_form.addRow("Host:", self._ollama_host)

        self._ollama_model = QLineEdit("llama3:latest")
        ollama_form.addRow("Model:", self._ollama_model)

        self._ollama_temp = QLineEdit("0.1")
        ollama_form.addRow("Temperature:", self._ollama_temp)

        self._ollama_tokens = QSpinBox()
        self._ollama_tokens.setRange(256, 32768)
        self._ollama_tokens.setValue(4096)
        ollama_form.addRow("Max Tokens:", self._ollama_tokens)

        layout.addWidget(ollama_card)

        # ── Security Policy ──
        security_card, security_form = _section_card("Security Policy")

        self._auto_approve_safe = _toggle(True)
        security_form.addRow("Auto-approve SAFE:", self._auto_approve_safe)

        self._auto_approve_low = _toggle(True)
        security_form.addRow("Auto-approve LOW_RISK:", self._auto_approve_low)

        self._require_medium = _toggle(True)
        security_form.addRow("Require approval MEDIUM:", self._require_medium)

        self._require_high = _toggle(True)
        security_form.addRow("Require approval HIGH:", self._require_high)

        self._block_high = _toggle(False)
        security_form.addRow("Block HIGH_RISK:", self._block_high)

        self._max_concurrent = QSpinBox()
        self._max_concurrent.setRange(1, 20)
        self._max_concurrent.setValue(5)
        security_form.addRow("Max Concurrent:", self._max_concurrent)

        layout.addWidget(security_card)

        # ── Execution Backends ──
        exec_card, exec_form = _section_card("Execution Backends")

        self._enable_wsl = _toggle(True)
        exec_form.addRow("Enable WSL2:", self._enable_wsl)

        self._enable_docker = _toggle(True)
        exec_form.addRow("Enable Docker:", self._enable_docker)

        self._default_timeout = QSpinBox()
        self._default_timeout.setRange(10, 3600)
        self._default_timeout.setValue(120)
        exec_form.addRow("Default Timeout (s):", self._default_timeout)

        layout.addWidget(exec_card)

        # ── Save ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save Settings")
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
