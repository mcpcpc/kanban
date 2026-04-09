"""Service for part CRUD operations."""

from sqlite3 import IntegrityError

from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.part import PartRepository
from kanban.services import ServiceResult


class PartService:
    def __init__(
        self,
        part_repo: PartRepository,
        kanban_repo: KanbanRepository,
    ) -> None:
        self.part_repo = part_repo
        self.kanban_repo = kanban_repo

    def list(self, *, search: str = "", category: str = "",
             page: int = 1, per_page: int = 20):
        parts, total_count = self.part_repo.find_all(
            search=search, category=category, page=page, per_page=per_page,
        )
        total_pages = (total_count + per_page - 1) // per_page
        categories = self.part_repo.get_categories()
        return parts, total_count, total_pages, categories

    def get_detail(self, part_id: int):
        part = self.part_repo.find_with_uom(part_id)
        if not part:
            return None, None
        kanbans = self.kanban_repo.find_by_part_id(part_id)
        return part, kanbans

    def get_units_of_measure(self):
        return self.part_repo.get_units_of_measure()

    def get_edit_context(self, part_id: int):
        part = self.part_repo.find_by_id(part_id)
        if not part:
            return None, None
        units = self.part_repo.get_units_of_measure()
        return part, units

    def create(self, *, part_number, manufacturer, description=None,
               category=None, datasheet=None, unit_of_measure_id,
               reorder_lead_time_days=7.0) -> ServiceResult:
        try:
            self.part_repo.create(
                part_number=part_number, manufacturer=manufacturer,
                description=description, category=category,
                datasheet=datasheet, unit_of_measure_id=unit_of_measure_id,
                reorder_lead_time_days=reorder_lead_time_days,
            )
        except IntegrityError:
            return ServiceResult(
                False,
                f"A part with number '{part_number}' already exists.",
                "danger",
            )
        return ServiceResult(True, f"Part '{part_number}' created successfully.")

    def update(self, part_id: int, *, part_number, manufacturer,
               description=None, category=None, datasheet=None,
               unit_of_measure_id, reorder_lead_time_days=7.0) -> ServiceResult:
        try:
            self.part_repo.update(
                part_id, part_number=part_number, manufacturer=manufacturer,
                description=description, category=category,
                datasheet=datasheet, unit_of_measure_id=unit_of_measure_id,
                reorder_lead_time_days=reorder_lead_time_days,
            )
        except IntegrityError:
            return ServiceResult(
                False,
                f"A part with number '{part_number}' already exists.",
                "danger",
            )
        return ServiceResult(True, f"Part '{part_number}' updated successfully.")

    def delete(self, part_id: int) -> ServiceResult:
        kanban_count = self.part_repo.count_kanbans(part_id)
        if kanban_count > 0:
            return ServiceResult(
                False,
                f"Cannot delete part: it is used in {kanban_count} kanban(s).",
                "danger",
            )
        part = self.part_repo.find_by_id(part_id)
        if not part:
            return ServiceResult(False, "Part not found.", "danger")
        self.part_repo.delete(part_id)
        return ServiceResult(True, f"Part '{part['part_number']}' deleted.")
