"""Entrypoint for the Insight desktop app.

Run from the repo root:
    source .venv/bin/activate
    python insight_desktop/app/main.py

Or double-click Insight.app on your Desktop (after running
insight_desktop/packaging/build_app.sh once).
"""

from __future__ import annotations

import sys
from pathlib import Path

_INSIGHT_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(_INSIGHT_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(_INSIGHT_DESKTOP_ROOT))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication, QSplashScreen  # noqa: E402

from app.logging_setup import setup_logging  # noqa: E402
from config.loader import load_config  # noqa: E402
from engine.interface import InsightEngine  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.theme import build_stylesheet  # noqa: E402

_ICON_PATH = _INSIGHT_DESKTOP_ROOT / "resources" / "icon.png"


def main() -> int:
    config = load_config()
    setup_logging(config)

    app = QApplication(sys.argv)
    app.setApplicationName(config.interaction.assistant_name)
    app.setApplicationDisplayName(config.interaction.assistant_name)
    app.setStyleSheet(build_stylesheet())

    icon = QIcon(str(_ICON_PATH)) if _ICON_PATH.exists() else QIcon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    splash = QSplashScreen(icon.pixmap(128, 128) if not icon.isNull() else None)
    splash.showMessage(
        "Loading models…",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        Qt.GlobalColor.white,
    )
    splash.show()
    app.processEvents()

    engine = InsightEngine(config)
    window = MainWindow(engine, assistant_name=config.interaction.assistant_name)
    window.show()
    splash.finish(window)
    window.raise_()
    window.activateWindow()

    exit_code = app.exec()
    engine.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
