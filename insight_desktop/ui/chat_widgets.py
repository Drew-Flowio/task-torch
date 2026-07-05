"""The chat transcript pane: read-only, auto-scrolling, with a welcome
empty state and polished message bubbles.
"""

from __future__ import annotations

import html

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit

from storage.models import Message
from ui import theme


def _wrap_html(body: str) -> str:
    return (
        f'<div style="font-family:{theme.FONT_UI}; '
        f'font-size:13px; line-height:1.55; color:{theme.INK};">'
        f"{body}</div>"
    )


def _empty_state(name: str) -> str:
    safe_name = html.escape(name)
    return f"""
<div style="text-align:center; padding:80px 40px; color:{theme.MUTED};">
  <div style="font-size:42px; margin-bottom:16px; opacity:0.35;">💬</div>
  <div style="font-size:16px; font-weight:600; color:{theme.INK_SECONDARY}; margin-bottom:8px;">
    Talk to {safe_name}
  </div>
  <div style="font-size:13px; line-height:1.5; max-width:320px; margin:0 auto;">
    Type a message below, or press the mic button to speak.<br>
    Everything stays on this machine — fully offline.
  </div>
</div>
"""


def _user_bubble(text: str) -> str:
    return (
        '<table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin:4px 0 10px 0;">'
        '<tr><td width="18%"></td><td align="right">'
        f'<span style="background:{theme.USER_BUBBLE}; color:{theme.USER_BUBBLE_TEXT}; '
        'padding:11px 16px; border-radius:18px 18px 4px 18px; '
        f'display:inline-block; max-width:72%; font-size:13px;">{text}</span>'
        '</td></tr></table>'
    )


def _assistant_bubble(name: str, text: str) -> str:
    safe_name = html.escape(name)
    return (
        '<table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin:4px 0 10px 0;">'
        '<tr><td width="36" valign="top" style="padding-top:2px;">'
        f'<div style="width:30px; height:30px; border-radius:15px; background:{theme.ACCENT}; '
        'color:white; font-size:14px; font-weight:700; text-align:center; '
        'line-height:30px;">I</div>'
        '</td><td align="left" style="padding-left:8px;">'
        f'<div style="color:{theme.MUTED}; font-size:11px; font-weight:600; '
        f'margin-bottom:4px; letter-spacing:0.3px;">{safe_name}</div>'
        f'<span style="background:{theme.ASSISTANT_BUBBLE}; color:{theme.INK}; '
        f'border:1px solid {theme.ASSISTANT_BUBBLE_BORDER}; '
        'padding:11px 16px; border-radius:4px 18px 18px 18px; '
        f'display:inline-block; max-width:72%; font-size:13px;">{text}</span>'
        '</td></tr></table>'
    )


def _typing_indicator(name: str) -> str:
    safe_name = html.escape(name)
    return (
        '<table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin:4px 0 10px 0;">'
        '<tr><td width="36" valign="top">'
        f'<div style="width:30px; height:30px; border-radius:15px; background:{theme.ACCENT}; '
        'color:white; font-size:14px; font-weight:700; text-align:center; '
        'line-height:30px;">I</div>'
        '</td><td align="left" style="padding-left:8px;">'
        f'<div style="color:{theme.MUTED}; font-size:11px; font-weight:600; margin-bottom:4px;">{safe_name}</div>'
        f'<span style="background:{theme.ASSISTANT_BUBBLE}; border:1px solid {theme.ASSISTANT_BUBBLE_BORDER}; '
        f'padding:11px 16px; border-radius:4px 18px 18px 18px; display:inline-block; color:{theme.MUTED};">'
        '<i>Thinking…</i></span>'
        '</td></tr></table>'
    )


class ChatTranscript(QTextEdit):
    def __init__(self, assistant_name: str = "Insight") -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setFrameStyle(0)
        self.setStyleSheet("QTextEdit { background: transparent; border: none; padding: 4px 2px; }")
        self._assistant_name = assistant_name
        self._messages: list[list[str]] = []
        self._show_typing = False

    def load_history(self, messages: list[Message]) -> None:
        self._messages = [[m.role, m.content] for m in messages if m.role in ("user", "assistant")]
        self._show_typing = False
        self._render()

    def add_user_message(self, text: str) -> None:
        self._messages.append(["user", text])
        self._show_typing = False
        self._render()

    def start_assistant_message(self) -> None:
        self._messages.append(["assistant", ""])
        self._show_typing = True
        self._render()

    def append_to_last_assistant(self, piece: str) -> None:
        if self._messages and self._messages[-1][0] == "assistant":
            self._show_typing = False
            self._messages[-1][1] += piece
            self._render()

    def finalize_last_assistant(self, final_text: str, cancelled: bool = False) -> None:
        if self._messages and self._messages[-1][0] == "assistant":
            self._show_typing = False
            suffix = (
                f'  <span style="color:{theme.MUTED_LIGHT}; font-size:11px;">(stopped)</span>'
                if cancelled else ""
            )
            self._messages[-1][1] = final_text
            self._render(final_suffix=suffix)

    def remove_last_assistant_if_empty(self) -> None:
        if self._messages and self._messages[-1][0] == "assistant" and not self._messages[-1][1]:
            self._messages.pop()
        self._show_typing = False
        self._render()

    def clear_transcript(self) -> None:
        self._messages = []
        self._show_typing = False
        self._render()

    def _render(self, final_suffix: str = "") -> None:
        if not self._messages and not self._show_typing:
            self.setHtml(_empty_state(self._assistant_name))
            return

        parts: list[str] = []
        last_index = len(self._messages) - 1

        for i, (role, text) in enumerate(self._messages):
            safe_text = html.escape(text).replace("\n", "<br>")
            if i == last_index and role == "assistant" and not self._show_typing:
                safe_text += final_suffix

            if role == "user":
                parts.append(_user_bubble(safe_text))
            elif text or (i == last_index and self._show_typing):
                if i == last_index and self._show_typing and not text:
                    parts.append(_typing_indicator(self._assistant_name))
                else:
                    parts.append(_assistant_bubble(self._assistant_name, safe_text))

        self.setHtml(_wrap_html("".join(parts)))
        self.moveCursor(QTextCursor.MoveOperation.End)
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
