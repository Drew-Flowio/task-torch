#!/usr/bin/env python3
"""Generate Insight app icon assets (PNG + macOS iconset source).

Run from repo root:
    .venv/bin/python insight_desktop/tools/generate_icon.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
PACKAGING = ROOT / "packaging" / "iconset_src"


def _draw_icon(size: int) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.08
    rect = pix.rect().adjusted(int(margin), int(margin), -int(margin), -int(margin))
    radius = size * 0.22

    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#3b82f6"))
    grad.setColorAt(1.0, QColor("#1d4ed8"))
    p.setBrush(grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(rect, radius, radius)

    # Subtle inner highlight
    highlight = QLinearGradient(rect.topLeft(), rect.center())
    highlight.setColorAt(0.0, QColor(255, 255, 255, 45))
    highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(highlight)
    p.drawRoundedRect(rect.adjusted(2, 2, -2, -int(rect.height() * 0.45)), radius, radius)

    # Letter "I" — bold, centered
    font = QFont("-apple-system", int(size * 0.42))
    font.setWeight(QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QPen(QColor("#ffffff")))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "I")

    # Small spark / insight dot upper-right
    dot_r = size * 0.055
    dot_x = rect.right() - size * 0.14
    dot_y = rect.top() + size * 0.18
    p.setBrush(QColor("#fbbf24"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(int(dot_x - dot_r), int(dot_y - dot_r), int(dot_r * 2), int(dot_r * 2))

    p.end()
    return pix


def main() -> None:
    app = QApplication(sys.argv)

    RESOURCES.mkdir(parents=True, exist_ok=True)
    PACKAGING.mkdir(parents=True, exist_ok=True)

    for size, path in [
        (512, PACKAGING / "icon_master.png"),
        (256, RESOURCES / "icon.png"),
    ]:
        pix = _draw_icon(size)
        ok = pix.save(str(path), "PNG")
        if not ok:
            raise SystemExit(f"Failed to write {path}")
        print(f"Wrote {path} ({size}x{size})")

    # Also write a 1024 master for Retina iconset @2x
    pix_1024 = _draw_icon(1024)
    pix_1024.save(str(PACKAGING / "icon_master@2x.png"), "PNG")
    print(f"Wrote {PACKAGING / 'icon_master@2x.png'} (1024x1024)")


if __name__ == "__main__":
    main()
