"""Touch UI interaction states for the Pi / Offgrid Minds microphone flow."""

from __future__ import annotations

from enum import Enum

from ui.touch import tokens as t


class TouchInteractionState(str, Enum):
    READY = "ready"
    OFFLINE = "offline"
    ONE_SHOT_RECORDING = "oneShotRecording"
    CONVERSATION_LISTENING = "conversationListening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    CONVERSATION_WAITING = "conversationWaiting"
    CAPTURING = "capturing"
    LOADING_PACK = "loadingPack"
    UPDATING_MEMORY = "updatingMemory"
    ERROR = "error"


HEADER_LABELS: dict[TouchInteractionState, str] = {
    TouchInteractionState.READY: "READY",
    TouchInteractionState.OFFLINE: "OFFLINE",
    TouchInteractionState.ONE_SHOT_RECORDING: "LISTENING",
    TouchInteractionState.CONVERSATION_LISTENING: "LISTENING",
    TouchInteractionState.TRANSCRIBING: "THINKING",
    TouchInteractionState.THINKING: "THINKING",
    TouchInteractionState.SPEAKING: "SPEAKING",
    TouchInteractionState.CONVERSATION_WAITING: "LISTENING",
    TouchInteractionState.CAPTURING: "CAPTURING",
    TouchInteractionState.LOADING_PACK: "LOADING PACK",
    TouchInteractionState.UPDATING_MEMORY: "UPDATING MEMORY",
    TouchInteractionState.ERROR: "ERROR",
}

# Voice-mode detail (shown under header status during conversation)
STATE_LABELS: dict[TouchInteractionState, str] = {
    TouchInteractionState.READY: "Ready",
    TouchInteractionState.ONE_SHOT_RECORDING: "Recording…",
    TouchInteractionState.CONVERSATION_LISTENING: "Conversation Mode",
    TouchInteractionState.TRANSCRIBING: "Thinking…",
    TouchInteractionState.THINKING: "Thinking…",
    TouchInteractionState.SPEAKING: "Speaking…",
    TouchInteractionState.CONVERSATION_WAITING: "Listening…",
    TouchInteractionState.CAPTURING: "Capturing…",
    TouchInteractionState.LOADING_PACK: "Loading pack…",
    TouchInteractionState.UPDATING_MEMORY: "Updating memory…",
    TouchInteractionState.ERROR: "Error",
}

STATE_COLORS: dict[TouchInteractionState, str] = {
    TouchInteractionState.READY: t.TEXT_TERTIARY,
    TouchInteractionState.OFFLINE: t.TEXT_TERTIARY,
    TouchInteractionState.ONE_SHOT_RECORDING: t.LISTENING,
    TouchInteractionState.CONVERSATION_LISTENING: t.CONVERSATION,
    TouchInteractionState.TRANSCRIBING: t.THINKING,
    TouchInteractionState.THINKING: t.THINKING,
    TouchInteractionState.SPEAKING: t.SPEAKING,
    TouchInteractionState.CONVERSATION_WAITING: t.CONVERSATION,
    TouchInteractionState.CAPTURING: t.ACCENT,
    TouchInteractionState.LOADING_PACK: t.THINKING,
    TouchInteractionState.UPDATING_MEMORY: t.THINKING,
    TouchInteractionState.ERROR: t.ERROR,
}
