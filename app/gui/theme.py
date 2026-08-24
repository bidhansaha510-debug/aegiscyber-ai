from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


COLORS = {
    "bg_primary": "#0a0e17",
    "bg_secondary": "#111827",
    "bg_tertiary": "#1a2332",
    "bg_card": "#151d2b",
    "bg_input": "#0d1420",
    "bg_hover": "#1e293b",
    "bg_selected": "#1e3a5f",
    "border": "#1e293b",
    "border_focus": "#3b82f6",
    "border_subtle": "#162032",
    "text_primary": "#e2e8f0",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "text_bright": "#f8fafc",
    "accent_blue": "#3b82f6",
    "accent_cyan": "#06b6d4",
    "accent_green": "#10b981",
    "accent_yellow": "#f59e0b",
    "accent_orange": "#f97316",
    "accent_red": "#ef4444",
    "accent_purple": "#8b5cf6",
    "accent_pink": "#ec4899",
    "status_safe": "#10b981",
    "status_low": "#3b82f6",
    "status_medium": "#f59e0b",
    "status_high": "#ef4444",
    "status_blocked": "#991b1b",
    "gradient_start": "#1e3a5f",
    "gradient_end": "#0a0e17",
    "kill_switch_bg": "#7f1d1d",
    "kill_switch_hover": "#991b1b",
    "kill_switch_active": "#ef4444",
}

RISK_COLORS = {
    "SAFE": COLORS["status_safe"],
    "LOW_RISK": COLORS["status_low"],
    "MEDIUM_RISK": COLORS["status_medium"],
    "HIGH_RISK": COLORS["status_high"],
    "BLOCKED": COLORS["status_blocked"],
}


def get_main_stylesheet() -> str:
    return f"""
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
    }}

    QWidget {{
        background-color: transparent;
        color: {COLORS['text_primary']};
        font-family: 'Segoe UI', 'Inter', sans-serif;
        font-size: 13px;
    }}

    QFrame {{
        border: none;
    }}

    QLabel {{
        color: {COLORS['text_primary']};
        background: transparent;
    }}

    QTextEdit, QPlainTextEdit {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 8px;
        font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
        font-size: 12px;
        selection-background-color: {COLORS['bg_selected']};
    }}

    QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {COLORS['border_focus']};
    }}

    QLineEdit {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 14px;
        selection-background-color: {COLORS['bg_selected']};
    }}

    QLineEdit:focus {{
        border-color: {COLORS['border_focus']};
    }}

    QLineEdit::placeholder {{
        color: {COLORS['text_muted']};
    }}

    QPushButton {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
        min-height: 32px;
    }}

    QPushButton:hover {{
        background-color: {COLORS['bg_hover']};
        border-color: {COLORS['accent_blue']};
    }}

    QPushButton:pressed {{
        background-color: {COLORS['bg_selected']};
    }}

    QPushButton:disabled {{
        color: {COLORS['text_muted']};
        background-color: {COLORS['bg_secondary']};
    }}

    QPushButton#primaryButton {{
        background-color: {COLORS['accent_blue']};
        border: none;
        color: white;
    }}

    QPushButton#primaryButton:hover {{
        background-color: #2563eb;
    }}

    QPushButton#dangerButton {{
        background-color: {COLORS['kill_switch_bg']};
        border: 1px solid {COLORS['accent_red']};
        color: {COLORS['accent_red']};
        font-weight: 700;
    }}

    QPushButton#dangerButton:hover {{
        background-color: {COLORS['kill_switch_hover']};
        color: white;
    }}

    QTabWidget::pane {{
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        background-color: {COLORS['bg_secondary']};
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 20px;
        margin-right: 2px;
        font-weight: 500;
    }}

    QTabBar::tab:selected {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['accent_cyan']};
        border-bottom: 2px solid {COLORS['accent_cyan']};
    }}

    QTabBar::tab:hover {{
        color: {COLORS['text_bright']};
        background-color: {COLORS['bg_hover']};
    }}

    QListWidget {{
        background-color: {COLORS['bg_input']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}

    QListWidget::item {{
        padding: 8px 12px;
        border-radius: 4px;
        margin: 1px 0px;
    }}

    QListWidget::item:selected {{
        background-color: {COLORS['bg_selected']};
        color: {COLORS['accent_cyan']};
    }}

    QListWidget::item:hover {{
        background-color: {COLORS['bg_hover']};
    }}

    QTreeWidget {{
        background-color: {COLORS['bg_input']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}

    QTreeWidget::item {{
        padding: 4px 8px;
    }}

    QTreeWidget::item:selected {{
        background-color: {COLORS['bg_selected']};
    }}

    QHeaderView::section {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        padding: 6px 12px;
        font-weight: 600;
    }}

    QTableWidget {{
        background-color: {COLORS['bg_input']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        gridline-color: {COLORS['border_subtle']};
    }}

    QTableWidget::item {{
        padding: 4px 8px;
    }}

    QTableWidget::item:selected {{
        background-color: {COLORS['bg_selected']};
    }}

    QScrollBar:vertical {{
        background-color: {COLORS['bg_primary']};
        width: 8px;
        border: none;
    }}

    QScrollBar::handle:vertical {{
        background-color: {COLORS['border']};
        border-radius: 4px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['text_muted']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {COLORS['bg_primary']};
        height: 8px;
        border: none;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {COLORS['border']};
        border-radius: 4px;
        min-width: 30px;
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    QProgressBar {{
        background-color: {COLORS['bg_input']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        text-align: center;
        height: 16px;
        color: {COLORS['text_primary']};
    }}

    QProgressBar::chunk {{
        background-color: {COLORS['accent_cyan']};
        border-radius: 3px;
    }}

    QSplitter::handle {{
        background-color: {COLORS['border']};
    }}

    QSplitter::handle:horizontal {{
        width: 2px;
    }}

    QSplitter::handle:vertical {{
        height: 2px;
    }}

    QGroupBox {{
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 16px;
        font-weight: 600;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {COLORS['accent_cyan']};
    }}

    QComboBox {{
        background-color: {COLORS['bg_input']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 6px 12px;
        color: {COLORS['text_primary']};
    }}

    QComboBox:hover {{
        border-color: {COLORS['border_focus']};
    }}

    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['bg_selected']};
    }}

    QCheckBox {{
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {COLORS['border']};
        border-radius: 3px;
        background-color: {COLORS['bg_input']};
    }}

    QCheckBox::indicator:checked {{
        background-color: {COLORS['accent_blue']};
        border-color: {COLORS['accent_blue']};
    }}

    QToolTip {{
        background-color: {COLORS['bg_card']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        padding: 6px 10px;
        border-radius: 4px;
    }}

    QMenuBar {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
        border-bottom: 1px solid {COLORS['border']};
        padding: 2px;
    }}

    QMenuBar::item:selected {{
        background-color: {COLORS['bg_hover']};
    }}

    QMenu {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 24px;
        border-radius: 3px;
    }}

    QMenu::item:selected {{
        background-color: {COLORS['bg_selected']};
    }}

    QStatusBar {{
        background-color: {COLORS['bg_primary']};
        border-top: 1px solid {COLORS['border']};
        color: {COLORS['text_secondary']};
    }}

    QDialog {{
        background-color: {COLORS['bg_secondary']};
    }}
    """
