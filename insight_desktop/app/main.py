"""Entrypoint for the Insight / Offgrid Minds app.

Desktop (default):
    python insight_desktop/app/main.py

Pi touch UI:
    python insight_desktop/app/main.py --config insight_desktop/config/config.pi.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_INSIGHT_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(_INSIGHT_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(_INSIGHT_DESKTOP_ROOT))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen  # noqa: E402

from app.logging_setup import setup_logging  # noqa: E402
from config.loader import DEFAULT_CONFIG_PATH, load_config  # noqa: E402
from engine.interface import InsightEngine  # noqa: E402

_ICON_PATH = _INSIGHT_DESKTOP_ROOT / "resources" / "icon.png"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Insight / Offgrid Minds")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to config YAML (use config.pi.yaml for touch UI)",
    )
    return parser.parse_args()


def _load_window(config, engine: InsightEngine) -> QMainWindow:
    if config.ui.mode == "touch":
        from ui.touch.live_transcript import SttPaths
        from ui.touch.main_window import TouchMainWindow

        stt = SttPaths(
            whisper_cli=config.resolve(config.models.whisper_cli_path),
            whisper_model=config.resolve(config.models.whisper_model_path),
            threads=config.models.whisper_threads,
            sample_rate=config.audio.sample_rate,
        )
        return TouchMainWindow(
            engine,
            assistant_name=config.ui.brand_name,
            screen_inches=config.ui.screen_inches,
            stt_paths=stt,
            input_device=config.audio.input_device,
        )

    from ui.main_window import MainWindow
    return MainWindow(engine, assistant_name=config.interaction.assistant_name)


def _load_stylesheet(config) -> str:
    if config.ui.mode == "touch":
        from ui.touch.stylesheet import build_stylesheet
        return build_stylesheet(config.ui.screen_inches)
    from ui.theme import build_stylesheet
    return build_stylesheet()


def main() -> int:
    args = _parse_args()
    config = load_config(args.config)
    setup_logging(config)

    app = QApplication(sys.argv)
    display_name = config.ui.brand_name if config.ui.mode == "touch" else config.interaction.assistant_name
    app.setApplicationName(display_name)
    app.setApplicationDisplayName(display_name)
    app.setStyleSheet(_load_stylesheet(config))

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
    window = _load_window(config, engine)
    window.show()
    if config.ui.mode == "touch" and config.ui.fullscreen:
        window.showFullScreen()
    splash.finish(window)
    window.raise_()
    window.activateWindow()

    exit_code = app.exec()
    engine.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
