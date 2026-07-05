"""Prepare assistant text for text-to-speech playback.

The chat UI shows the full reply; Piper only gets the spoken portion —
stripped of markup and truncated at the long-answer handoff phrase.
"""

from __future__ import annotations

import re

SPOKEN_HANDOFF = "I'll put the longer details in text for you."

# Bracketed / angle-bracket tags like [DEBUG] or <system>.
_TAG_RE = re.compile(r"\[[^\]]+\]|<[^>]+>")
# Fenced code blocks — replaced with a short spoken cue, not read verbatim.
_FENCED_CODE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
# Markdown headings (# Title).
_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
# Bold / italic markers.
_EMPHASIS_RE = re.compile(r"\*\*([^*]+)\*\*|\*([^*]+)\*|__([^_]+)__|_([^_]+)_")
# Inline backticks.
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
# Leading list markers (-, *, •, 1.).
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+\.)\s+", re.MULTILINE)
# Hashtags used as markup (#heading-style), not inside words.
_HASHTAG_RE = re.compile(r"(?<=\s)#(\w+)")
# Common emoji ranges.
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def prepare_for_speech(text: str) -> str:
    """Return the portion of `text` that should be read aloud."""
    spoken = _truncate_at_handoff(text)
    spoken = _strip_markup(spoken)
    return re.sub(r"\s+", " ", spoken).strip()


def _truncate_at_handoff(text: str) -> str:
    lower = text.lower()
    marker = SPOKEN_HANDOFF.lower()
    idx = lower.find(marker)
    if idx == -1:
        return text
    return text[: idx + len(SPOKEN_HANDOFF)]


def _strip_markup(text: str) -> str:
    text = _FENCED_CODE_RE.sub("There's a code snippet in the text.", text)
    text = _TAG_RE.sub("", text)
    text = _HEADING_RE.sub("", text)
    text = _EMPHASIS_RE.sub(lambda m: m.group(1) or m.group(2) or m.group(3) or m.group(4) or "", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _LIST_MARKER_RE.sub("", text)
    text = _HASHTAG_RE.sub(r"\1", text)
    text = _EMOJI_RE.sub("", text)
    return text.replace("*", "").replace("#", "")
