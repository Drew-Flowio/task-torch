"""Shared design tokens and the application stylesheet.

Keeping colors, typography, and component styles in one place makes it
easy to iterate on the look without hunting through individual widgets.
"""

from __future__ import annotations

# Brand palette
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
ACCENT_PRESSED = "#1e40af"
ACCENT_SOFT = "#eff6ff"
ACCENT_MUTED = "#93c5fd"

DANGER = "#dc2626"
DANGER_HOVER = "#b91c1c"
DANGER_SOFT = "#fef2f2"

SUCCESS = "#16a34a"
WARNING = "#d97706"

INK = "#111827"
INK_SECONDARY = "#374151"
MUTED = "#6b7280"
MUTED_LIGHT = "#9ca3af"

BORDER = "#e5e7eb"
BORDER_STRONG = "#d1d5db"

APP_BG = "#f3f4f6"
SURFACE = "#ffffff"
SURFACE_RAISED = "#fafafa"
CHAT_BG = "#f9fafb"

USER_BUBBLE = "#2563eb"
USER_BUBBLE_TEXT = "#ffffff"
ASSISTANT_BUBBLE = "#ffffff"
ASSISTANT_BUBBLE_BORDER = "#e5e7eb"

FONT_UI = '-apple-system, "SF Pro Text", "Segoe UI", system-ui, sans-serif'
FONT_MONO = 'Menlo, Monaco, "SF Mono", Consolas, monospace'

STATUS_COLORS = {
    "idle": MUTED_LIGHT,
    "listening": DANGER,
    "transcribing": WARNING,
    "thinking": WARNING,
    "speaking": SUCCESS,
    "error": DANGER,
}

STATUS_LABELS = {
    "idle": "Ready",
    "listening": "Listening…",
    "transcribing": "Transcribing…",
    "thinking": "Thinking…",
    "speaking": "Speaking…",
    "error": "Error",
}


def build_stylesheet() -> str:
    return f"""
QMainWindow {{ background: {APP_BG}; }}
QWidget {{
    font-family: {FONT_UI};
    color: {INK};
    font-size: 13px;
}}

/* ---- Header ---- */
QWidget#headerBar {{
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}
QLabel#titleLabel {{
    font-size: 15px;
    font-weight: 600;
    color: {INK};
    letter-spacing: -0.2px;
}}
QLabel#subtitleLabel {{
    font-size: 11px;
    color: {MUTED};
    font-weight: 400;
}}
QWidget#statusPill {{
    background: {SURFACE_RAISED};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QLabel#statusDot {{
    border-radius: 4px;
    background: {MUTED_LIGHT};
    min-width: 8px;
    max-width: 8px;
    min-height: 8px;
    max-height: 8px;
}}

/* ---- Chat panel ---- */
QWidget#chatPanel {{
    background: {CHAT_BG};
    border-right: 1px solid {BORDER};
}}
QWidget#inputBar {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 14px;
}}
QWidget#inputBar:focus-within {{
    border: 1px solid {ACCENT_MUTED};
}}

/* ---- Buttons ---- */
QPushButton {{
    background: {SURFACE};
    color: {INK_SECONDARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: 10px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
}}
QPushButton:hover:!disabled {{ background: {SURFACE_RAISED}; border-color: {BORDER}; }}
QPushButton:pressed:!disabled {{ background: #eef0f3; }}
QPushButton:disabled {{
    color: {MUTED_LIGHT};
    background: #f3f4f6;
    border-color: {BORDER};
}}

QPushButton#primaryButton {{
    background: {ACCENT};
    color: white;
    border: none;
    font-weight: 600;
    padding: 8px 20px;
}}
QPushButton#primaryButton:hover:!disabled {{ background: {ACCENT_HOVER}; }}
QPushButton#primaryButton:pressed:!disabled {{ background: {ACCENT_PRESSED}; }}
QPushButton#primaryButton:disabled {{ background: {ACCENT_MUTED}; color: #dbeafe; }}

QPushButton#micButton {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    font-size: 16px;
    font-weight: 700;
    padding: 0px;
}}
QPushButton#micButton:hover:!disabled {{ background: {ACCENT_HOVER}; }}
QPushButton#micButton[recording="true"] {{ background: {DANGER}; }}
QPushButton#micButton[recording="true"]:hover:!disabled {{ background: {DANGER_HOVER}; }}
QPushButton#micButton:disabled {{ background: {ACCENT_MUTED}; }}

QPushButton#ghostButton {{
    background: transparent;
    border: 1px solid transparent;
    color: {MUTED};
    padding: 6px 12px;
}}
QPushButton#ghostButton:hover:!disabled {{
    background: {SURFACE_RAISED};
    border-color: {BORDER};
    color: {INK_SECONDARY};
}}

QPushButton#dangerButton {{
    color: {DANGER};
    border-color: #fecaca;
    background: {DANGER_SOFT};
}}
QPushButton#dangerButton:hover:!disabled {{ background: #fee2e2; border-color: #fca5a5; }}

/* ---- Inputs ---- */
QLineEdit, QPlainTextEdit {{
    border: 1px solid {BORDER_STRONG};
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    background: {SURFACE};
    color: {INK};
    selection-background-color: {ACCENT};
    selection-color: white;
}}
QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {ACCENT}; }}
QWidget#inputBar QLineEdit {{
    border: none;
    background: transparent;
    padding: 10px 6px;
    font-size: 14px;
}}

/* ---- Inspector ---- */
QWidget#inspectorPanel {{
    background: {SURFACE};
}}
QTabWidget::pane {{
    border: none;
    background: {SURFACE};
    top: 0px;
}}
QTabBar {{
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 10px 16px;
    font-size: 12px;
    font-weight: 600;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
}}
QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover:!selected {{ color: {INK_SECONDARY}; }}

QListWidget {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    background: {SURFACE_RAISED};
    outline: none;
    padding: 4px;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 8px;
    color: {INK_SECONDARY};
    margin: 1px 0;
}}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}
QListWidget::item:hover:!selected {{ background: #f3f4f6; }}

QLabel#sectionLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {MUTED};
    letter-spacing: 0.6px;
    padding-top: 2px;
    padding-bottom: 2px;
}}
QLabel#cardLabel {{
    color: {INK_SECONDARY};
    padding: 12px 14px;
    background: {SURFACE_RAISED};
    border: 1px solid {BORDER};
    border-radius: 10px;
    font-size: 12px;
    line-height: 1.4;
}}

/* ---- Scrollbars ---- */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: #d1d5db;
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: #9ca3af; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}

QSplitter::handle {{ background: {BORDER}; width: 1px; }}
"""
