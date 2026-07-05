"""Dev utility: renders the main window with a canned demo conversation
(mock mode, offscreen-friendly) and saves a PNG screenshot for quick
visual review of UI/style changes without needing to click through the
app by hand.

Usage (from repo root):
    QT_QPA_PLATFORM=offscreen .venv/bin/python insight_desktop/tools/render_preview.py
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

_INSIGHT_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(_INSIGHT_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(_INSIGHT_DESKTOP_ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.main import _ICON_PATH  # noqa: E402
from ui.theme import build_stylesheet  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from config.loader import load_config  # noqa: E402
from engine.interface import InsightEngine  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


def main() -> None:
    config = replace(load_config(), mock_mode=True)

    app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    if _ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(_ICON_PATH)))

    engine = InsightEngine(config)
    window = MainWindow(engine, assistant_name=config.interaction.assistant_name)
    window.resize(1180, 760)

    window._transcript.add_user_message("The check engine light just came on, what do I do?")
    window._transcript.start_assistant_message()
    window._transcript.finalize_last_assistant(
        "Yeah, that's worth checking before you drive much further. Pop the gas cap "
        "back on tight first, that's the most common cause. If the light's still on "
        "tomorrow, get the code read at a parts store, they'll do it free."
    )
    window._transcript.add_user_message("It's tight already.")
    window._transcript.start_assistant_message()
    window._transcript.finalize_last_assistant(
        "Okay, then don't ignore it. Get the code pulled before you put more miles on it."
    )

    window.show()
    app.processEvents()

    pixmap = window.grab()
    out_path = Path(__file__).resolve().parent / "preview.png"
    pixmap.save(str(out_path))
    print(f"Saved {out_path}")

    engine.shutdown()


if __name__ == "__main__":
    main()
