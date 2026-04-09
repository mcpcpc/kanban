"""Service for location CRUD operations."""

from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.location import LocationRepository
from kanban.services import ServiceResult


class LocationService:
    def __init__(
        self,
        location_repo: LocationRepository,
        kanban_repo: KanbanRepository,
    ) -> None:
        self.location_repo = location_repo
        self.kanban_repo = kanban_repo

    def list(self, *, search: str = "", color: str = ""):
        locations = self.location_repo.find_all(search=search, color=color)
        kanban_counts = self.location_repo.get_kanban_counts()
        colors_in_use = self.location_repo.get_colors_in_use()
        return locations, kanban_counts, colors_in_use

    def get_detail(self, location_id: int):
        location = self.location_repo.find_by_id(location_id)
        if not location:
            return None, None
        kanbans = self.kanban_repo.find_by_location_id(location_id)
        return location, kanbans

    def get_edit_context(self, location_id: int):
        return self.location_repo.find_by_id(location_id)

    def create(self, *, location, description=None, color=None) -> ServiceResult:
        try:
            self.location_repo.create(
                location=location, description=description, color=color,
            )
        except Exception as e:
            return ServiceResult(False, f"Error creating location: {e}", "danger")
        return ServiceResult(True, f"Location '{location}' created successfully.")

    def update(self, location_id: int, *, location, description=None,
               color=None) -> ServiceResult:
        self.location_repo.update(
            location_id, location=location,
            description=description, color=color,
        )
        return ServiceResult(True, f"Location '{location}' updated successfully.")

    def delete(self, location_id: int) -> ServiceResult:
        kanban_count = self.location_repo.count_kanbans(location_id)
        if kanban_count > 0:
            return ServiceResult(
                False,
                f"Cannot delete location: it is used in {kanban_count} kanban(s).",
                "danger",
            )
        location = self.location_repo.find_by_id(location_id)
        if not location:
            return ServiceResult(False, "Location not found.", "danger")
        self.location_repo.delete(location_id)
        return ServiceResult(True, f"Location '{location['location']}' deleted.")
