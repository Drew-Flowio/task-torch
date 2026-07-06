"""Qt stylesheet for the Offgrid Minds Pi touch UI."""

from __future__ import annotations

from ui.touch import tokens as t


def build_stylesheet(screen_inches: int = 7) -> str:
    scale = 0.9 if screen_inches <= 5 else 1.0
    body = int(t.FONT_BODY * scale)
    caption = int(t.FONT_CAPTION * scale)
    brand = int(t.FONT_BRAND * scale)
    tagline = int(t.FONT_TAGLINE * scale)
    micro = int(t.FONT_MICRO * scale)
    touch = t.MIN_TOUCH

    return f"""
QMainWindow, QWidget {{
    background: {t.BG};
    color: {t.TEXT_PRIMARY};
    font-family: {t.FONT_UI};
    font-size: {body}px;
}}
QLabel {{ background: transparent; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.BORDER};
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* Header */
QWidget#instrumentHeader {{
    background: {t.BG};
    border-bottom: 1px solid {t.BORDER};
}}
QLabel#brandName {{
    font-family: {t.FONT_DISPLAY};
    font-size: {brand}px;
    font-weight: 700;
    letter-spacing: 2.5px;
    color: {t.TEXT_SOFT_WHITE};
}}
QLabel#brandTagline {{
    font-size: {tagline}px;
    font-weight: 500;
    letter-spacing: 1.2px;
    color: {t.TEXT_TERTIARY};
    text-transform: uppercase;
}}
QWidget#headerStatus {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_CHIP}px;
}}
QLabel#headerStatusLabel {{
    font-size: {caption}px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {t.TEXT_SOFT_WHITE};
}}
QLabel#headerChip {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_CHIP}px;
    padding: 4px 8px;
    font-size: {micro}px;
    font-weight: 600;
    letter-spacing: 0.8px;
    color: {t.TEXT_SECONDARY};
}}
QPushButton#headerIconBtn {{
    background: {t.SURFACE};
    color: {t.TEXT_SECONDARY};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_BUTTON}px;
    min-width: {touch}px;
    max-width: {touch}px;
    min-height: {touch}px;
    max-height: {touch}px;
    font-size: {body}px;
    padding: 0;
}}
QPushButton#headerIconBtn:pressed {{
    background: {t.SURFACE_RAISED};
    border-color: {t.ACCENT_DIM};
}}

/* Main split */
QWidget#cameraShell {{ background: transparent; }}
QWidget#cameraViewport {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: {t.RADIUS_CARD}px;
}}
QFrame#cameraFrame {{
    background: #0A0A0C;
    border: none;
    border-radius: {t.RADIUS_CARD}px;
}}
QLabel#cameraPlaceholder {{
    color: {t.TEXT_TERTIARY};
    font-size: {caption}px;
}}
QLabel#liveBadge {{
    background: {t.SURFACE};
    border: 1px solid {t.ACCENT_DIM};
    border-radius: 6px;
    padding: 2px 8px;
    font-size: {micro}px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {t.LIVE};
}}
QLabel#zoomBadge {{
    font-size: {micro}px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: {t.TEXT_TERTIARY};
}}
QPushButton#cameraHudBtn {{
    background: {t.SURFACE};
    color: {t.TEXT_SOFT_WHITE};
    border: 1px solid {t.BORDER};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: {micro}px;
    font-weight: 700;
    letter-spacing: 1px;
    min-height: 32px;
}}
QPushButton#cameraHudBtn:pressed {{
    background: {t.SURFACE_RAISED};
    border-color: {t.ACCENT_DIM};
}}

/* Prompt bar */
QWidget#promptBar {{ background: transparent; }}
QLineEdit#promptInput {{
    background: {t.SURFACE};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS}px;
    padding: 0 14px;
    min-height: {touch}px;
    font-size: {body}px;
    selection-background-color: {t.ACCENT_SOFT};
}}
QLineEdit#promptInput:focus {{
    border-color: {t.ACCENT_DIM};
}}
QPushButton#promptSendBtn {{
    background: {t.ACCENT};
    color: #0D0D0F;
    border: none;
    border-radius: {t.RADIUS}px;
    font-size: 18px;
    font-weight: 700;
}}
QPushButton#promptSendBtn:pressed {{
    background: {t.ACCENT_DIM};
}}
QPushButton#promptSendBtn:disabled {{
    background: {t.SURFACE_RAISED};
    color: {t.TEXT_TERTIARY};
}}

/* AI panel */
QScrollArea#aiPanel {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_CARD}px;
}}
QLabel#aiPanelTitle {{
    font-size: {caption}px;
    font-weight: 700;
    letter-spacing: 1.4px;
    color: {t.TEXT_TERTIARY};
    padding: 12px 12px 0 12px;
}}
QLabel#aiModeLabel {{
    font-size: {caption}px;
    font-weight: 600;
    letter-spacing: 0.6px;
    color: {t.ACCENT};
    padding: 2px 12px 0 12px;
}}
QFrame#aiSectionCard {{
    background: {t.SURFACE_RAISED};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: 10px;
    margin: 0 10px;
}}
QLabel#aiSectionTitle {{
    font-size: {micro}px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#aiSectionBody {{
    font-size: {body}px;
    color: {t.TEXT_PRIMARY};
    line-height: 1.4;
}}
QLabel#aiIdleLabel {{
    font-size: {caption}px;
    color: {t.TEXT_TERTIARY};
    letter-spacing: 0.3px;
}}

/* Bottom action bar */
QWidget#bottomActionBar {{
    background: {t.BG};
    border-top: 1px solid {t.BORDER};
}}
QFrame#actionCard {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_CARD}px;
}}
QFrame#actionCard[active="true"] {{
    border-color: {t.ACCENT};
    background: {t.SURFACE_RAISED};
}}
QFrame#actionCard[mic="true"][active="true"] {{
    border-color: {t.ACCENT};
}}
QFrame#actionCard:disabled {{
    opacity: 0.5;
}}
QLabel#actionCardIcon {{
    font-size: 20px;
    color: {t.TEXT_SOFT_WHITE};
}}
QLabel#actionCardTitle {{
    font-size: {micro}px;
    font-weight: 700;
    letter-spacing: 0.9px;
    color: {t.TEXT_SOFT_WHITE};
}}
QLabel#actionCardSubtitle {{
    font-size: {micro - 1}px;
    color: {t.TEXT_TERTIARY};
    letter-spacing: 0.2px;
}}
QPushButton#micActionBtn {{
    background: {t.SURFACE_RAISED};
    color: {t.TEXT_SOFT_WHITE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS}px;
    font-size: 22px;
}}
QPushButton#micActionBtn:pressed {{
    background: {t.BORDER};
}}
QPushButton#micActionBtn[recording="true"] {{
    background: {t.ERROR};
    color: white;
    border-color: {t.ERROR};
}}
QPushButton#micActionBtn[conversation="true"] {{
    background: {t.ACCENT};
    color: #0D0D0F;
    border-color: {t.ACCENT};
}}
QPushButton#micActionBtn[pulsing="true"] {{
    border: 2px solid {t.ACCENT};
}}
QPushButton#micActionBtn:disabled {{
    background: {t.SURFACE};
    color: {t.TEXT_TERTIARY};
}}
QPushButton#micEndBtn {{
    background: transparent;
    color: {t.ERROR};
    border: 1px solid {t.ERROR};
    border-radius: 8px;
    font-size: {micro}px;
    font-weight: 600;
    padding: 2px 8px;
    max-height: 24px;
}}

/* Sheets */
QDialog#touchSheet {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
}}
QLabel#sheetTitle {{
    font-size: {brand}px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {t.TEXT_SOFT_WHITE};
}}
QListWidget {{
    background: {t.BG};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_CARD}px;
    color: {t.TEXT_PRIMARY};
    font-size: {body}px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 10px;
    border-radius: 8px;
}}
QListWidget::item:selected {{
    background: {t.ACCENT_SOFT};
    color: {t.ACCENT};
}}
QPushButton#secondaryButton {{
    background: {t.SURFACE};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_BUTTON}px;
    min-height: {touch}px;
    font-weight: 600;
    padding: 0 16px;
}}
QPushButton#secondaryButton:pressed {{
    background: {t.SURFACE_RAISED};
}}
QPushButton#dangerButton {{
    background: {t.SURFACE};
    color: {t.ERROR};
    border: 1px solid {t.ERROR};
    border-radius: {t.RADIUS_BUTTON}px;
    min-height: {touch}px;
    font-weight: 600;
    padding: 0 16px;
}}
QMessageBox {{
    background: {t.SURFACE};
    color: {t.TEXT_PRIMARY};
}}

/* Mode switcher */
QWidget#modeSwitcher {{ background: transparent; }}
QPushButton#modeBtn {{
    background: {t.SURFACE};
    color: {t.TEXT_SECONDARY};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS}px;
    min-height: {touch}px;
    font-size: {caption}px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QPushButton#modeBtn:checked, QPushButton#modeBtn[active="true"] {{
    background: {t.SURFACE_RAISED};
    color: {t.ACCENT};
    border-color: {t.ACCENT_DIM};
}}

/* Expert pack strip */
QWidget#expertPackStrip {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS}px;
    padding: 0 4px;
}}
QLabel#expertPackLabel {{
    font-size: {micro}px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {t.TEXT_TERTIARY};
    padding-left: 8px;
}}
QLabel#expertPackName {{
    font-size: {caption}px;
    font-weight: 600;
    color: {t.TEXT_SOFT_WHITE};
}}
QLabel#expertPackMeta {{
    font-size: {micro}px;
    color: {t.TEXT_TERTIARY};
}}
QPushButton#expertPackSwitchBtn {{
    background: transparent;
    color: {t.ACCENT};
    border: 1px solid {t.ACCENT_DIM};
    border-radius: 8px;
    padding: 4px 12px;
    font-size: {micro}px;
    font-weight: 600;
    min-height: 28px;
}}

/* Scan capture */
QPushButton#scanCaptureBtn {{
    background: {t.ACCENT};
    color: #0D0D0F;
    border: none;
    border-radius: {t.RADIUS}px;
    font-size: {caption}px;
    font-weight: 700;
    letter-spacing: 1.2px;
}}
QPushButton#scanCaptureBtn:pressed {{ background: {t.ACCENT_DIM}; }}
QPushButton#scanCaptureBtn:disabled {{
    background: {t.SURFACE_RAISED};
    color: {t.TEXT_TERTIARY};
}}

/* Talk mode */
QLabel#talkSectionTitle {{
    font-size: {micro}px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: {t.TEXT_TERTIARY};
}}
QPlainTextEdit#liveTranscript {{
    background: {t.SURFACE};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS}px;
    padding: 10px;
    font-size: {body}px;
}}
QPushButton#talkSendBtn {{
    background: {t.ACCENT};
    color: #0D0D0F;
    border: none;
    border-radius: {t.RADIUS}px;
    font-weight: 700;
    padding: 0 16px;
}}
QLabel#talkHint {{
    font-size: {micro}px;
    color: {t.TEXT_TERTIARY};
}}

/* Chat mode */
QPushButton#chatBackBtn {{
    background: {t.SURFACE};
    color: {t.TEXT_SOFT_WHITE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS}px;
    min-height: {touch}px;
    padding: 0 14px;
    font-weight: 600;
}}
QTextEdit#chatTranscript {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS}px;
    padding: 8px;
}}
QLineEdit#chatInput {{
    background: {t.SURFACE};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS}px;
    padding: 0 12px;
    font-size: {body}px;
}}
QPushButton#chatSendBtn {{
    background: {t.ACCENT};
    color: #0D0D0F;
    border: none;
    border-radius: {t.RADIUS}px;
    font-weight: 700;
}}
QLabel#sheetHint {{
    font-size: {caption}px;
    color: {t.TEXT_TERTIARY};
    padding-bottom: 6px;
}}
"""
