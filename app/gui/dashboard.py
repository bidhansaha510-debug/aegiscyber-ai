from __future__ import annotations

from typing import Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QGroupBox, QProgressBar,
)
from PySide6.QtCore import Qt

from app.gui.theme import COLORS


class StatCard(QFrame):
    def __init__(self, title: str, value: str, icon: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setMinimumSize(200, 100)
        self.setStyleSheet(
            f"QFrame#statCard {{ background-color: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 10px; "
            f"border-left: 4px solid {color}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        header = QLabel(f"{icon} {title}")
        header.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; "
            f"font-weight: 600; text-transform: uppercase; background: transparent;"
        )
        layout.addWidget(header)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            f"color: {color}; font-size: 28px; font-weight: 700; background: transparent;"
        )
        layout.addWidget(self._value_label)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)


class DashboardPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Dashboard")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLORS['text_bright']};"
        )
        layout.addWidget(title)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self._investigations_card = StatCard("Investigations", "0", "[*]", COLORS["accent_cyan"])
        self._tools_card = StatCard("Tools Available", "0", "[#]", COLORS["accent_blue"])
        self._executions_card = StatCard("Commands Executed", "0", "[>]", COLORS["accent_green"])
        self._entities_card = StatCard("OSINT Entities", "0", "[@]", COLORS["accent_purple"])

        cards_layout.addWidget(self._investigations_card)
        cards_layout.addWidget(self._tools_card)
        cards_layout.addWidget(self._executions_card)
        cards_layout.addWidget(self._entities_card)
        layout.addLayout(cards_layout)

        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(16)

        system_group = QGroupBox("System Status")
        system_layout = QVBoxLayout(system_group)
        system_layout.setSpacing(10)

        self._ollama_label = QLabel("Ollama: Checking...")
        self._ollama_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        system_layout.addWidget(self._ollama_label)

        self._wsl_label = QLabel("WSL2 Backend: Checking...")
        self._wsl_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        system_layout.addWidget(self._wsl_label)

        self._docker_label = QLabel("Docker Backend: Checking...")
        self._docker_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        system_layout.addWidget(self._docker_label)

        self._gpu_label = QLabel("GPU: Checking...")
        self._gpu_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        system_layout.addWidget(self._gpu_label)

        system_layout.addStretch()
        mid_layout.addWidget(system_group, 1)

        scope_group = QGroupBox("Current Scope")
        scope_layout = QVBoxLayout(scope_group)

        self._scope_label = QLabel("No scope defined")
        self._scope_label.setWordWrap(True)
        self._scope_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-style: italic;")
        scope_layout.addWidget(self._scope_label)
        scope_layout.addStretch()
        mid_layout.addWidget(scope_group, 1)

        layout.addLayout(mid_layout, 1)

    def update_stats(
        self,
        investigations: int = 0,
        tools: int = 0,
        executions: int = 0,
        entities: int = 0,
    ) -> None:
        self._investigations_card.set_value(str(investigations))
        self._tools_card.set_value(str(tools))
        self._executions_card.set_value(str(executions))
        self._entities_card.set_value(str(entities))

    def update_tools_count(self, installed: int, total: int) -> None:
        self._tools_card.set_value(f"{installed}/{total}")

    def update_status(self, data: dict[str, Any]) -> None:
        ollama_ok = data.get("ollama", False)
        backends = data.get("backends", {})
        gpu = data.get("gpu", False)
        self.update_system_status(
            ollama=ollama_ok,
            wsl=backends.get("wsl2", False),
            docker=backends.get("docker", False),
            gpu=gpu,
        )
        self._tools_card.set_value(f"{data.get('installed_count', 0)}/{data.get('tools_count', 0)}")

    def update_system_status(
        self,
        ollama: bool = False,
        wsl: bool = False,
        docker: bool = False,
        gpu: dict | bool = False,
    ) -> None:
        self._set_status_label(self._ollama_label, "Ollama", ollama)
        self._set_status_label(self._wsl_label, "WSL2", wsl)
        self._set_status_label(self._docker_label, "Docker", docker)
        
        if isinstance(gpu, dict):
            if gpu.get("available", False):
                name = gpu.get("name", "GPU")
                detail = gpu.get("detail", f"{name} Available")
                self._gpu_label.setText(f"[+] GPU: {detail}")
                self._gpu_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 13px;")
            else:
                self._gpu_label.setText("[-] GPU: Unavailable")
                self._gpu_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        elif gpu:
            self._gpu_label.setText("[+] GPU: Available")
            self._gpu_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 13px;")
        else:
            self._gpu_label.setText("[-] GPU: Unavailable")
            self._gpu_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")

    def _set_status_label(self, label: QLabel, name: str, available: bool) -> None:
        icon = "[+]" if available else "[-]"
        color = COLORS["accent_green"] if available else COLORS["accent_red"]
        label.setText(f"{icon} {name}: {'Available' if available else 'Unavailable'}")
        label.setStyleSheet(f"color: {color}; font-size: 13px;")

    def update_scope(self, scope_text: str) -> None:
        self._scope_label.setText(scope_text)
        self._scope_label.setStyleSheet(f"color: {COLORS['text_primary']};")
