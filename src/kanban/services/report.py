"""Service for the reports page."""

from kanban.repositories.event import EventRepository
from kanban.repositories.kanban import KanbanRepository


class ReportService:
    def __init__(
        self,
        event_repo: EventRepository,
        kanban_repo: KanbanRepository,
    ) -> None:
        self.event_repo = event_repo
        self.kanban_repo = kanban_repo

    def get_report(self) -> dict:
        total_events = self.event_repo.count_all()
        total_kanbans = self.kanban_repo.count_active()
        events_by_type = self.event_repo.count_by_type()
        active_kanbans = self.kanban_repo.get_most_active(limit=10)
        cycle_times = self.event_repo.get_cycle_times()

        avg_cycle_days = None
        if cycle_times:
            total_days = sum(row["days"] for row in cycle_times if row["days"])
            avg_cycle_days = total_days / len(cycle_times) if cycle_times else None

        return {
            "total_events": total_events,
            "total_kanbans": total_kanbans,
            "events_by_type": events_by_type,
            "active_kanbans": active_kanbans,
            "avg_cycle_days": avg_cycle_days,
        }
