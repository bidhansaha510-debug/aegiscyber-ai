from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import QTimer

from app.gui.theme import COLORS


class StatusBarWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(20)

        self._app_label = QLabel("AegisCyber AI v1.0.0")
        self._app_label.setStyleSheet(
            f"color: {COLORS['accent_cyan']}; font-weight: 700; font-size: 12px;"
        )
        layout.addWidget(self._app_label)

        self._ollama_status = QLabel("[●] Ollama: Checking...")
        self._ollama_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self._ollama_status)

        self._backend_status = QLabel("[●] Backends: --")
        self._backend_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self._backend_status)

        self._gpu_label = QLabel("[●] GPU: --")
        self._gpu_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self._gpu_label)

        self._tool_count = QLabel("Tools: --")
        self._tool_count.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(self._tool_count)

        layout.addStretch()

        self._kill_status = QLabel("")
        self._kill_status.setStyleSheet(f"color: {COLORS['accent_red']}; font-weight: 700; font-size: 11px;")
        layout.addWidget(self._kill_status)

    def set_ollama_status(self, connected: bool, model: str = "") -> None:
        if connected:
            text = f"[●] Ollama: Connected ({model})" if model else "[●] Ollama: Connected"
            self._ollama_status.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 11px;")
        else:
            text = "[●] Ollama: Disconnected"
            self._ollama_status.setStyleSheet(f"color: {COLORS['accent_red']}; font-size: 11px;")
        self._ollama_status.setText(text)

    def set_backend_status(self, backends: dict[str, bool]) -> None:
        parts = []
        for name, available in backends.items():
            status = "[+]" if available else "[-]"
            parts.append(f"{status} {name}")
        self._backend_status.setText(f"[●] Backends: {', '.join(parts)}")
        any_available = any(backends.values())
        color = COLORS['accent_green'] if any_available else COLORS['accent_red']
        self._backend_status.setStyleSheet(f"color: {color}; font-size: 11px;")

    def set_gpu_status(self, gpu_info: dict | bool, usage: int = 0) -> None:
        if isinstance(gpu_info, dict):
            if gpu_info.get("available", False):
                name = gpu_info.get("name", "GPU")
                temp = gpu_info.get("temperature_c", 0)
                mem_used = gpu_info.get("memory_used_mb", 0)
                mem_total = gpu_info.get("memory_total_mb", 0)
                if mem_total > 0:
                    mem_str = f"{mem_used/1024:.1f}/{mem_total/1024:.1f} GB"
                else:
                    mem_str = "Active"
                temp_str = f", {temp}°C" if temp > 0 else ""
                self._gpu_label.setText(f"[●] GPU: {name} ({mem_str}{temp_str})")
                self._gpu_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 11px;")
            else:
                self._gpu_label.setText("[○] GPU: N/A")
                self._gpu_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        elif gpu_info:
            self._gpu_label.setText(f"[●] GPU: Active ({usage}%)")
            self._gpu_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 11px;")
        else:
            self._gpu_label.setText("[○] GPU: N/A")
            self._gpu_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")

    def set_tool_count(self, installed: int, total: int) -> None:
        self._tool_count.setText(f"Tools: {installed}/{total}")

    def set_kill_switch(self, engaged: bool) -> None:
        if engaged:
            self._kill_status.setText("[!] EMERGENCY STOP ACTIVE")
        else:
            self._kill_status.setText("")
