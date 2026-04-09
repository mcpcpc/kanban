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

    def get_health(self) -> dict:
        total_kanbans = self.kanban_repo.count_active()
        total_parts = self.event_repo.db.execute("SELECT COUNT(*) FROM part").fetchone()[0]
        total_locations = self.event_repo.db.execute("SELECT COUNT(*) FROM location").fetchone()[0]
        total_events = self.event_repo.count_all()
        pending_signals = self.event_repo.count_pending_signal_kanbans()

        return {
            "total_kanbans": total_kanbans,
            "total_parts": total_parts,
            "total_locations": total_locations,
            "total_events": total_events,
            "pending_signals": pending_signals,
            "health": {
                "healthy": total_kanbans - pending_signals,
                "warning": pending_signals,
                "critical": 0,
            },
        }

    def get_metrics(self) -> dict:
        events_7d = self.event_repo.get_events_in_period(days=7)
        cycle = self.event_repo.get_avg_cycle_time()
        return {
            "events_7d": {row["type"]: row["count"] for row in events_7d},
            "avg_cycle_time_days": cycle["avg_days"] if cycle else None,
        }
