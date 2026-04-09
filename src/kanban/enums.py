"""Canonical enumerations for the kanban domain."""

from enum import StrEnum


class EventType(StrEnum):
    """Kanban event types — mirrors the ``kanban_event_type`` seed data."""

    SIGNAL = "signal"
    RESTOCK_START = "restock_start"
    RESTOCK_COMPLETE = "restock_complete"
    ADJUSTMENT = "adjustment"

    @property
    def label(self) -> str:
        """Human-readable label for flash messages and UI display."""
        return _EVENT_LABELS[self]


_EVENT_LABELS: dict["EventType", str] = {
    EventType.SIGNAL: "Signal recorded",
    EventType.RESTOCK_START: "Restock started",
    EventType.RESTOCK_COMPLETE: "Restock complete",
    EventType.ADJUSTMENT: "Adjustment recorded",
}


class InventoryStatus(StrEnum):
    """Inventory health classification."""

    OK = "ok"
    LOW = "low"
    WARNING = "warning"
    OUT = "out"
