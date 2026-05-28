"""Service for processing barcode scans (web + DataWedge)."""

from logging import info

from kanban.enums import EventType
from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.event import EventRepository
from kanban.repositories.inventory import InventoryRepository
from kanban.services import ServiceResult
from kanban.utils.calculations import parse_barcode


class ScanService:
    def __init__(
        self,
        kanban_repo: KanbanRepository,
        event_repo: EventRepository,
        inventory_repo: InventoryRepository,
    ) -> None:
        self.kanban_repo = kanban_repo
        self.event_repo = event_repo
        self.inventory_repo = inventory_repo

    def process_scan(
        self,
        barcode: str,
        action: str = "signal",
        quantity: str = "",
        notes: str = "",
        user_id: int | None = None,
    ) -> ServiceResult:
        """Validate and record a scan event.  Returns a ``ServiceResult``."""
        if not barcode:
            return ServiceResult(False, "No barcode scanned.", "danger")

        kanban_id = parse_barcode(barcode)
        if not kanban_id:
            return ServiceResult(False, f"Invalid barcode format: {barcode}", "danger")

        kanban = self.kanban_repo.find_with_part_location(kanban_id)
        if not kanban:
            return ServiceResult(False, f"Kanban not found: {barcode}", "danger")

        label = f"{kanban['part_name']} @ {kanban['location_name']}"

        if not kanban["is_active"]:
            return ServiceResult(False, f"Kanban is inactive: {label}", "warning")

        open_signals = self.event_repo.get_open_signal_count(kanban_id)

        # Validate signal: can't exceed number_of_cards
        if action == EventType.SIGNAL:
            if open_signals >= kanban["number_of_cards"]:
                return ServiceResult(
                    False,
                    f"All {kanban['number_of_cards']} cards already signaled for "
                    f"{label} — waiting for restock",
                    "warning",
                )

        # Validate restock: require an open signal
        if action in (EventType.RESTOCK_START, EventType.RESTOCK_COMPLETE):
            if open_signals <= 0:
                verb = "start restocking" if action == EventType.RESTOCK_START else "complete restocking"
                return ServiceResult(
                    False,
                    f"Cannot {verb}: no open signal for {label}",
                    "danger",
                )

        # Resolve event type
        try:
            event_type = EventType(action)
        except ValueError:
            return ServiceResult(False, f"Invalid action: {action}", "danger")

        event_type_id = self.event_repo.get_event_type_id(event_type)
        if not event_type_id:
            return ServiceResult(False, f"Invalid action: {action}", "danger")

        # Parse quantity
        qty = None
        if quantity:
            try:
                qty = int(quantity)
            except ValueError:
                return ServiceResult(False, "Invalid quantity.", "danger")

        # Record event
        self.event_repo.create(kanban_id, event_type_id, qty, notes or None, user_id)

        # Decrease inventory on signal
        if event_type is EventType.SIGNAL:
            self.inventory_repo.decrease_quantity(
                kanban["part_id"], kanban["kanban_quantity"]
            )

        self.kanban_repo.db.commit()

        msg = f"{event_type.label}: {label}"
        if qty is not None:
            msg += f" (qty: {qty})"

        info(msg)
        return ServiceResult(True, msg)

    def process_datawedge_scan(self, barcode: str) -> None:
        """Simplified scan path used by the DataWedge TCP handler.

        Always records a ``signal`` — validation failures are logged, not
        returned as flash messages.
        """
        result = self.process_scan(barcode)
        if not result.success:
            info(result.message)
