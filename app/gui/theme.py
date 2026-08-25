from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

COLORS = {
    
    "bg_void":            "#0B0E14",
    "bg_surface":         "#12161F",
    "bg_surface_raised":  "#1A1F2B",

   
    "border_hairline":    "#232938",

   
    "text_primary":       "#E4E7EE",
    "text_muted":         "#7C8494",


    "accent":             "#5EA1FF",
    "accent_hover":       "#4A8DE6",   
    "accent_pressed":     "#3A7BD4",   
    "state_clear":        "#3DD68C",
    "state_review":       "#E8A33D",
    "state_caution":      "#E5484D",
    "state_blocked":      "#8A1F2B",
}


COLORS.update({

    "bg_primary":     COLORS["bg_void"],
    "bg_secondary":   COLORS["bg_surface"],
    "bg_tertiary":    COLORS["bg_surface_raised"],
    "bg_card":        COLORS["bg_surface_raised"],
    "bg_input":       COLORS["bg_void"],
    "bg_hover":       COLORS["bg_surface_raised"],
    "bg_selected":    "#1E3050",  

    "border":         COLORS["border_hairline"],
    "border_focus":   COLORS["accent"],
    "border_subtle":  COLORS["border_hairline"],

    
    "text_secondary": COLORS["text_muted"],
    "text_bright":    COLORS["text_primary"],

    "accent_blue":    COLORS["accent"],
    "accent_cyan":    COLORS["accent"],
    "accent_green":   COLORS["state_clear"],
    "accent_yellow":  COLORS["state_review"],
    "accent_orange":  COLORS["state_review"],
    "accent_red":     COLORS["state_caution"],
    "accent_purple":  COLORS["accent"],
    "accent_pink":    COLORS["accent"],


    "status_safe":    COLORS["state_clear"],
    "status_low":     COLORS["state_clear"],
    "status_medium":  COLORS["state_review"],
    "status_high":    COLORS["state_caution"],
    "status_blocked": COLORS["state_blocked"],

    "kill_switch_bg":     COLORS["state_blocked"],
    "kill_switch_hover":  "#A12535",
    "kill_switch_active": COLORS["state_caution"],
})


RISK_COLORS = {
    "SAFE":        COLORS["state_clear"],
    "LOW_RISK":    COLORS["state_clear"],
    "MEDIUM_RISK": COLORS["state_review"],
    "HIGH_RISK":   COLORS["state_caution"],
    "BLOCKED":     COLORS["state_blocked"],
}



FONT_SANS  = "'Inter', 'IBM Plex Sans', 'Segoe UI', sans-serif"
FONT_MONO  = "'JetBrains Mono', 'IBM Plex Mono', 'Cascadia Code', 'Consolas', monospace"


def get_main_stylesheet() -> str:
    C = COLORS
    return f"""

    /* ── Base ────────────────────────────────────────────────── */

    QMainWindow {{
        background-color: {C['bg_void']};
    }}

    QWidget {{
        background-color: transparent;
        color: {C['text_primary']};
        font-family: {FONT_SANS};
        font-size: 13px;
    }}

    QFrame {{
        border: none;
    }}

    QLabel {{
        color: {C['text_primary']};
        background: transparent;
    }}


    /* ── Text Inputs ─────────────────────────────────────────── */

    QTextEdit, QPlainTextEdit {{
        background-color: {C['bg_void']};
        color: {C['text_primary']};
        border: 1px solid {C['border_hairline']};
        border-radius: 8px;
        padding: 8px;
        font-family: {FONT_MONO};
        font-size: 12px;
        selection-background-color: {C['bg_selected']};
    }}

    QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {C['accent']};
    }}

    QLineEdit {{
        background-color: {C['bg_void']};
        color: {C['text_primary']};
        border: 1px solid {C['border_hairline']};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        selection-background-color: {C['bg_selected']};
    }}

    QLineEdit:focus {{
        border-color: {C['accent']};
    }}

    QLineEdit::placeholder {{
        color: {C['text_muted']};
    }}


    /* ── Buttons — Default (Secondary) ───────────────────────── */

    QPushButton {{
        background-color: transparent;
        color: {C['text_primary']};
        border: 1px solid {C['border_hairline']};
        border-radius: 8px;
        padding: 8px 16px;
        font-family: {FONT_SANS};
        font-weight: 600;
        min-height: 32px;
    }}

    QPushButton:hover {{
        background-color: {C['bg_surface_raised']};
        border-color: {C['accent']};
        color: {C['text_primary']};
    }}

    QPushButton:pressed {{
        background-color: {C['bg_selected']};
    }}

    QPushButton:disabled {{
        color: {C['text_muted']};
        background-color: {C['bg_surface']};
        border-color: {C['border_hairline']};
    }}

    /* ── Buttons — Primary (accent fill) ─────────────────────── */

    QPushButton#primaryButton {{
        background-color: {C['accent']};
        border: 1px solid {C['accent']};
        color: #FFFFFF;
        font-weight: 700;
    }}

    QPushButton#primaryButton:hover {{
        background-color: {C['accent_hover']};
        border-color: {C['accent_hover']};
    }}

    QPushButton#primaryButton:pressed {{
        background-color: {C['accent_pressed']};
        border-color: {C['accent_pressed']};
    }}

    QPushButton#primaryButton:disabled {{
        background-color: {C['bg_surface_raised']};
        border-color: {C['border_hairline']};
        color: {C['text_muted']};
    }}

    /* ── Buttons — Secondary (explicit, matches default) ─────── */

    QPushButton#secondaryButton {{
        background-color: transparent;
        border: 1px solid {C['border_hairline']};
        color: {C['text_primary']};
        font-weight: 600;
    }}

    QPushButton#secondaryButton:hover {{
        background-color: {C['bg_surface_raised']};
        border-color: {C['accent']};
    }}

    /* ── Buttons — Destructive (Emergency Stop) ──────────────── */

    QPushButton#dangerButton {{
        background-color: {C['state_blocked']};
        border: 1px solid {C['state_caution']};
        color: {C['state_caution']};
        font-weight: 800;
    }}

    QPushButton#dangerButton:hover {{
        background-color: {C['state_caution']};
        border-color: {C['state_caution']};
        color: #FFFFFF;
    }}

    QPushButton#dangerButton:pressed {{
        background-color: #7A1520;
    }}


    /* ── Tabs ────────────────────────────────────────────────── */

    QTabWidget::pane {{
        border: 1px solid {C['border_hairline']};
        background-color: {C['bg_surface']};
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: transparent;
        color: {C['text_muted']};
        border: none;
        border-bottom: 2px solid transparent;
        padding: 8px 24px;
        margin-right: 4px;
        font-family: {FONT_SANS};
        font-weight: 500;
        font-size: 13px;
    }}

    QTabBar::tab:selected {{
        color: {C['accent']};
        border-bottom: 2px solid {C['accent']};
    }}

    QTabBar::tab:hover {{
        color: {C['text_primary']};
    }}


    /* ── Lists ───────────────────────────────────────────────── */

    QListWidget {{
        background-color: {C['bg_void']};
        border: 1px solid {C['border_hairline']};
        border-radius: 8px;
        padding: 4px;
        outline: none;
    }}

    QListWidget::item {{
        padding: 8px 12px;
        border-radius: 4px;
        margin: 1px 0px;
    }}

    QListWidget::item:selected {{
        background-color: {C['bg_selected']};
        color: {C['accent']};
    }}

    QListWidget::item:hover {{
        background-color: {C['bg_surface_raised']};
    }}


    /* ── Trees ───────────────────────────────────────────────── */

    QTreeWidget {{
        background-color: {C['bg_void']};
        border: 1px solid {C['border_hairline']};
        border-radius: 8px;
        padding: 4px;
        outline: none;
    }}

    QTreeWidget::item {{
        padding: 4px 8px;
    }}

    QTreeWidget::item:selected {{
        background-color: {C['bg_selected']};
    }}


    /* ── Tables ──────────────────────────────────────────────── */

    QHeaderView::section {{
        background-color: {C['bg_surface_raised']};
        color: {C['text_muted']};
        border: none;
        border-bottom: 1px solid {C['border_hairline']};
        border-right: 1px solid {C['border_hairline']};
        padding: 8px 12px;
        font-family: {FONT_SANS};
        font-weight: 600;
        font-size: 12px;
    }}

    QTableWidget {{
        background-color: {C['bg_surface']};
        border: 1px solid {C['border_hairline']};
        border-radius: 8px;
        gridline-color: {C['border_hairline']};
    }}

    QTableWidget::item {{
        padding: 4px 8px;
        border-bottom: 1px solid {C['border_hairline']};
    }}

    QTableWidget::item:selected {{
        background-color: {C['bg_selected']};
    }}


    /* ── Scrollbars ──────────────────────────────────────────── */

    QScrollBar:vertical {{
        background-color: {C['bg_void']};
        width: 8px;
        border: none;
    }}

    QScrollBar::handle:vertical {{
        background-color: {C['border_hairline']};
        border-radius: 4px;
        min-height: 32px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {C['text_muted']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {C['bg_void']};
        height: 8px;
        border: none;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {C['border_hairline']};
        border-radius: 4px;
        min-width: 32px;
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}


    /* ── Progress Bars ───────────────────────────────────────── */

    QProgressBar {{
        background-color: {C['bg_void']};
        border: 1px solid {C['border_hairline']};
        border-radius: 4px;
        text-align: center;
        height: 16px;
        color: {C['text_primary']};
    }}

    QProgressBar::chunk {{
        background-color: {C['accent']};
        border-radius: 4px;
    }}


    /* ── Splitters ───────────────────────────────────────────── */

    QSplitter::handle {{
        background-color: {C['border_hairline']};
    }}

    QSplitter::handle:horizontal {{
        width: 2px;
    }}

    QSplitter::handle:vertical {{
        height: 2px;
    }}


    /* ── Group Boxes ─────────────────────────────────────────── */

    QGroupBox {{
        background-color: {C['bg_surface_raised']};
        border: 1px solid {C['border_hairline']};
        border-radius: 8px;
        margin-top: 8px;
        padding: 24px 16px 16px 16px;
        font-weight: 600;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 8px;
        color: {C['text_primary']};
        font-family: {FONT_SANS};
        font-weight: 600;
    }}


    /* ── Combo Boxes ─────────────────────────────────────────── */

    QComboBox {{
        background-color: {C['bg_void']};
        border: 1px solid {C['border_hairline']};
        border-radius: 8px;
        padding: 8px 12px;
        color: {C['text_primary']};
        font-family: {FONT_SANS};
    }}

    QComboBox:hover {{
        border-color: {C['accent']};
    }}

    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {C['bg_surface']};
        border: 1px solid {C['border_hairline']};
        selection-background-color: {C['bg_selected']};
    }}


    /* ── Checkboxes (default) ────────────────────────────────── */

    QCheckBox {{
        spacing: 8px;
        font-family: {FONT_SANS};
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {C['border_hairline']};
        border-radius: 4px;
        background-color: {C['bg_void']};
    }}

    QCheckBox::indicator:hover {{
        border-color: {C['accent']};
    }}

    QCheckBox::indicator:checked {{
        background-color: {C['accent']};
        border-color: {C['accent']};
    }}

    /* ── Toggle Switch (objectName = toggleSwitch) ────────────── */

    QCheckBox#toggleSwitch {{
        spacing: 8px;
    }}

    QCheckBox#toggleSwitch::indicator {{
        width: 40px;
        height: 22px;
        border-radius: 11px;
        border: 1px solid {C['border_hairline']};
        background-color: {C['bg_surface_raised']};
    }}

    QCheckBox#toggleSwitch::indicator:checked {{
        background-color: {C['accent']};
        border-color: {C['accent']};
    }}

    QCheckBox#toggleSwitch::indicator:hover {{
        border-color: {C['accent']};
    }}


    /* ── Spin Boxes ──────────────────────────────────────────── */

    QSpinBox {{
        background-color: {C['bg_void']};
        border: 1px solid {C['border_hairline']};
        border-radius: 8px;
        padding: 8px 12px;
        color: {C['text_primary']};
        font-family: {FONT_MONO};
    }}

    QSpinBox:focus {{
        border-color: {C['accent']};
    }}

    QSpinBox::up-button, QSpinBox::down-button {{
        border: none;
        width: 20px;
    }}


    /* ── Tooltips ─────────────────────────────────────────────── */

    QToolTip {{
        background-color: {C['bg_surface_raised']};
        color: {C['text_primary']};
        border: 1px solid {C['border_hairline']};
        padding: 8px;
        border-radius: 4px;
        font-family: {FONT_SANS};
        font-size: 12px;
    }}


    /* ── Menu Bar ─────────────────────────────────────────────── */

    QMenuBar {{
        background-color: {C['bg_void']};
        color: {C['text_primary']};
        border-bottom: 1px solid {C['border_hairline']};
        padding: 4px;
    }}

    QMenuBar::item:selected {{
        background-color: {C['bg_surface_raised']};
    }}

    QMenu {{
        background-color: {C['bg_surface']};
        border: 1px solid {C['border_hairline']};
        padding: 4px;
    }}

    QMenu::item {{
        padding: 8px 24px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {C['bg_selected']};
    }}


    /* ── Status Bar ──────────────────────────────────────────── */

    QStatusBar {{
        background-color: {C['bg_void']};
        border-top: 1px solid {C['border_hairline']};
        color: {C['text_muted']};
    }}


    /* ── Dialogs ─────────────────────────────────────────────── */

    QDialog {{
        background-color: {C['bg_surface']};
    }}


    /* ── Scroll Areas ────────────────────────────────────────── */

    QScrollArea {{
        border: none;
        background-color: transparent;
    }}

    """
