"""Service for kanban CRUD and printing."""

from kanban.enums import EventType
from kanban.protocols import Printer
from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.event import EventRepository
from kanban.repositories.part import PartRepository
from kanban.repositories.setting import SettingRepository
from kanban.services import ServiceResult
from kanban.zebra import KanbanLabelTemplate


class KanbanService:
    def __init__(
        self,
        kanban_repo: KanbanRepository,
        event_repo: EventRepository,
        part_repo: PartRepository,
        setting_repo: SettingRepository,
        printer_factory: type | None = None,
    ) -> None:
        self.kanban_repo = kanban_repo
        self.event_repo = event_repo
        self.part_repo = part_repo
        self.setting_repo = setting_repo
        self._printer_factory = printer_factory

    def list(self, search: str = "", status: str = ""):
        return self.kanban_repo.find_all(search=search, status=status)

    def get_detail(self, kanban_id: int):
        kanban = self.kanban_repo.find_with_details(kanban_id)
        if not kanban:
            return None, None
        events = self.event_repo.find_by_kanban_id(kanban_id)
        return kanban, events

    def get_edit_context(self, kanban_id: int):
        kanban = self.kanban_repo.get_with_lead_time(kanban_id)
        if not kanban:
            return None, None, None
        parts = self.part_repo.find_all(per_page=9999)[0]
        from kanban.repositories.location import LocationRepository
        locations = LocationRepository(self.kanban_repo.db).find_all()
        return kanban, parts, locations

    def create(self, *, part_id, location_id, kanban_quantity,
               safety_lead_time_days, estimated_daily_demand, is_active) -> ServiceResult:
        try:
            kanban_quantity = int(kanban_quantity) if kanban_quantity else 100
            safety_lead_time_days = float(safety_lead_time_days) if safety_lead_time_days else 0
            estimated_daily_demand = float(estimated_daily_demand) if estimated_daily_demand else 0
        except ValueError:
            return ServiceResult(False, "Invalid quantity values.", "danger")

        if not part_id or not location_id:
            return ServiceResult(False, "Part and Location are required.", "danger")

        lead_time = self.part_repo.get_lead_time(int(part_id))
        new_id = self.kanban_repo.create(
            part_id=part_id, location_id=location_id,
            kanban_quantity=kanban_quantity,
            safety_lead_time_days=safety_lead_time_days,
            estimated_daily_demand=estimated_daily_demand,
            lead_time_days=lead_time, is_active=is_active,
        )
        return ServiceResult(True, "Kanban created successfully.", data={"id": new_id})

    def update(self, kanban_id: int, *, part_id, location_id, kanban_quantity,
               safety_lead_time_days, estimated_daily_demand, is_active) -> ServiceResult:
        try:
            kanban_quantity = int(kanban_quantity) if kanban_quantity else 100
            safety_lead_time_days = float(safety_lead_time_days) if safety_lead_time_days else 0
            estimated_daily_demand = float(estimated_daily_demand) if estimated_daily_demand else 0
        except ValueError:
            return ServiceResult(False, "Invalid quantity values.", "danger")

        if not part_id or not location_id:
            return ServiceResult(False, "Part and Location are required.", "danger")

        lead_time = self.part_repo.get_lead_time(int(part_id))
        self.kanban_repo.update(
            kanban_id, part_id=part_id, location_id=location_id,
            kanban_quantity=kanban_quantity,
            safety_lead_time_days=safety_lead_time_days,
            estimated_daily_demand=estimated_daily_demand,
            lead_time_days=lead_time, is_active=is_active,
        )
        return ServiceResult(True, "Kanban updated successfully.")

    def delete(self, kanban_id: int) -> ServiceResult:
        event_count = self.kanban_repo.count_events(kanban_id)
        if event_count > 0:
            return ServiceResult(
                False,
                f"Cannot delete kanban: it has {event_count} event(s). "
                "Consider deactivating instead.",
                "danger",
            )
        self.kanban_repo.delete(kanban_id)
        return ServiceResult(True, "Kanban deleted.")

    def print_cards(self, kanban_id: int) -> ServiceResult:
        kanban = self.kanban_repo.find_with_details(kanban_id)
        if not kanban:
            return ServiceResult(False, "Kanban not found.", "danger")

        settings = self.setting_repo.get()
        if self._printer_factory is None:
            return ServiceResult(False, "No printer configured.", "danger")

        printer: Printer = self._printer_factory(
            settings["printer_hostname"],
            settings["printer_port"],
            settings["printer_timeout_seconds"],
        )
        try:
            for i in range(1, kanban["number_of_cards"] + 1):
                label = KanbanLabelTemplate(**kanban)
                zpl = label.render(i, settings["label_template"])
                printer.print(zpl)
        except Exception as e:
            return ServiceResult(False, f"Print failed: {e}", "danger")

        return ServiceResult(True, "Kanban card(s) printed.")
