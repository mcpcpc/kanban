"""Service for inventory listing, adjustments, and export."""

from datetime import datetime, timedelta

from kanban.enums import EventType
from kanban.repositories.event import EventRepository
from kanban.repositories.inventory import InventoryRepository
from kanban.repositories.kanban import KanbanRepository
from kanban.services import ServiceResult
from kanban.utils.calculations import determine_inventory_status


ITEMS_PER_PAGE = 20


class InventoryService:
    def __init__(
        self,
        inventory_repo: InventoryRepository,
        event_repo: EventRepository,
        kanban_repo: KanbanRepository,
    ) -> None:
        self.inventory_repo = inventory_repo
        self.event_repo = event_repo
        self.kanban_repo = kanban_repo

    def calculate_demand_stats(self, part_id: int, days: int = 30) -> dict:
        since_date = datetime.now() - timedelta(days=days)
        total_restocked = self.event_repo.get_demand_total(part_id, since_date)
        avg_daily_demand = total_restocked / days if days > 0 else 0
        return {
            "total_restocked": total_restocked,
            "avg_daily_demand": avg_daily_demand,
            "period_days": days,
        }

    def list(self, *, search: str = "", status_filter: str = "",
             page: int = 1):
        parts = self.inventory_repo.find_all_with_details(search=search)
        inventory_data = []
        for part in parts:
            stats = self.calculate_demand_stats(part["id"])
            days_of_supply = None
            if stats["avg_daily_demand"] > 0:
                days_of_supply = part["quantity_on_hand"] / stats["avg_daily_demand"]
            status = determine_inventory_status(
                part["quantity_on_hand"],
                part["total_reorder_point"],
                days_of_supply,
                part["reorder_lead_time_days"],
            )
            if status_filter and status != status_filter:
                continue
            inventory_data.append({
                "part": part,
                "avg_daily_demand": stats["avg_daily_demand"],
                "days_of_supply": days_of_supply,
                "status": status,
                "total_kanban_quantity": part["total_kanban_quantity"],
                "total_reorder_point": part["total_reorder_point"],
            })

        total_count = len(inventory_data)
        total_pages = max(1, (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        start = (page - 1) * ITEMS_PER_PAGE
        return inventory_data[start:start + ITEMS_PER_PAGE], total_count, total_pages

    def adjust(self, part_id: int, part, *, adjustment_type: str,
               quantity: float, reason: str) -> ServiceResult:
        if adjustment_type == "set":
            new_quantity = quantity
        elif adjustment_type == "add":
            new_quantity = part["quantity_on_hand"] + quantity
        elif adjustment_type == "subtract":
            new_quantity = part["quantity_on_hand"] - quantity
        else:
            new_quantity = quantity

        new_quantity = max(0.0, new_quantity)

        self.inventory_repo.upsert(part_id, new_quantity, reason or None)

        # Record adjustment events for related kanbans
        kanbans = self.kanban_repo.find_active_by_part_id(part_id)
        adjustment_type_id = self.event_repo.get_event_type_id(EventType.ADJUSTMENT)
        adjustment_qty = new_quantity - part["quantity_on_hand"]
        note = f"Inventory adjustment: {reason}" if reason else "Inventory adjustment"
        for kanban in kanbans:
            self.event_repo.create(kanban["id"], adjustment_type_id, adjustment_qty, note)

        self.inventory_repo.db.commit()
        return ServiceResult(
            True,
            f"Inventory updated: {part['part_number']} now has {new_quantity} {part['uom_abbr']}.",
        )

    def export_data(self):
        """Return all inventory rows enriched with demand / status."""
        parts = self.inventory_repo.find_all_with_details()
        rows = []
        for part in parts:
            stats = self.calculate_demand_stats(part["id"])
            days_of_supply = None
            if stats["avg_daily_demand"] > 0:
                days_of_supply = part["quantity_on_hand"] / stats["avg_daily_demand"]
            status = determine_inventory_status(
                part["quantity_on_hand"],
                part["total_reorder_point"],
                days_of_supply,
                part["reorder_lead_time_days"],
            )
            rows.append({
                "part": part,
                "avg_daily_demand": stats["avg_daily_demand"],
                "days_of_supply": days_of_supply,
                "status": status,
            })
        return rows
