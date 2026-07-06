"""UI-only Expert Pack registry — switching is local until backend packs ship."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpertPack:
    id: str
    name: str
    version: str
    source: str
    trust: str


PACKS: tuple[ExpertPack, ...] = (
    ExpertPack("general", "General Field", "1.0.0", "Offgrid Minds", "Verified · On-device"),
    ExpertPack("electrical", "Electrical", "1.2.0", "Offgrid Minds", "Verified · On-device"),
    ExpertPack("automotive", "Automotive", "0.9.1", "Offgrid Minds", "Verified · On-device"),
    ExpertPack("wilderness", "Wilderness", "1.0.0", "Community Pack", "Reviewed · Offline"),
)

DEFAULT_PACK_ID = "general"


class ExpertPackStore:
    """Tracks the active pack in UI state only."""

    def __init__(self) -> None:
        self._active_id = DEFAULT_PACK_ID

    @property
    def active(self) -> ExpertPack:
        for pack in PACKS:
            if pack.id == self._active_id:
                return pack
        return PACKS[0]

    def set_active(self, pack_id: str) -> ExpertPack:
        for pack in PACKS:
            if pack.id == pack_id:
                self._active_id = pack_id
                return pack
        return self.active

    def all_packs(self) -> tuple[ExpertPack, ...]:
        return PACKS
