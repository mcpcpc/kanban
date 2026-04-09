"""Service for the dashboard overview."""

from datetime import datetime, timedelta

from kanban.repositories.event import EventRepository
from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.part import PartRepository
from kanban.repositories.location import LocationRepository
from kanban.utils.calculations import build_30_day_trend


class DashboardService:
    def __init__(
        self,
        kanban_repo: KanbanRepository,
        event_repo: EventRepository,
        part_repo: PartRepository,
        location_repo: LocationRepository,
    ) -> None:
        self.kanban_repo = kanban_repo
        self.event_repo = event_repo
        self.part_repo = part_repo
        self.location_repo = location_repo

    def get_overview(self) -> dict:
        total_parts = self.part_repo.count_all()
        total_locations = self.location_repo.count_all()
        total_kanbans = self.kanban_repo.count_active()

        recent_events = self.event_repo.find_recent_with_details(limit=10)
        pending_signals_raw = self.event_repo.get_pending_signals()

        pending_signals = [
            {**dict(row), "signal_time": datetime.fromisoformat(row["signal_time"])}
            for row in pending_signals_raw
        ]
        active_signals = len(pending_signals)

        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        kanban_trend, kanban_max = build_30_day_trend(
            self.kanban_repo.get_30_day_creation_trend(thirty_days_ago)
        )
        parts_trend, parts_max = build_30_day_trend(
            self.part_repo.get_30_day_creation_trend(thirty_days_ago)
        )
        locations_trend, locations_max = build_30_day_trend(
            self.location_repo.get_30_day_creation_trend(thirty_days_ago)
        )
        signals_trend, signals_max = build_30_day_trend(
            self.event_repo.get_30_day_signal_trend(thirty_days_ago)
        )

        return {
            "total_parts": total_parts,
            "total_locations": total_locations,
            "total_kanbans": total_kanbans,
            "active_signals": active_signals,
            "pending_signals": pending_signals,
            "recent_events": recent_events,
            "current_time": datetime.now(),
            "kanban_trend": kanban_trend,
            "kanban_max": kanban_max,
            "parts_trend": parts_trend,
            "parts_max": parts_max,
            "locations_trend": locations_trend,
            "locations_max": locations_max,
            "signals_trend": signals_trend,
            "signals_max": signals_max,
        }
