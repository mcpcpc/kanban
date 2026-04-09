"""Request-scoped dependency injection helpers.

All factory functions cache their result on ``quart.g`` so repositories
and services are created at most once per request.
"""

from quart import g

from kanban.db import get_db
from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.event import EventRepository
from kanban.repositories.part import PartRepository
from kanban.repositories.location import LocationRepository
from kanban.repositories.inventory import InventoryRepository
from kanban.repositories.setting import SettingRepository
from kanban.services.scan import ScanService
from kanban.services.kanban import KanbanService
from kanban.services.inventory import InventoryService
from kanban.services.dashboard import DashboardService
from kanban.services.report import ReportService
from kanban.zebra import ZebraPrinter


def get_kanban_repo() -> KanbanRepository:
    if not hasattr(g, "_kanban_repo"):
        g._kanban_repo = KanbanRepository(get_db())
    return g._kanban_repo


def get_event_repo() -> EventRepository:
    if not hasattr(g, "_event_repo"):
        g._event_repo = EventRepository(get_db())
    return g._event_repo


def get_part_repo() -> PartRepository:
    if not hasattr(g, "_part_repo"):
        g._part_repo = PartRepository(get_db())
    return g._part_repo


def get_location_repo() -> LocationRepository:
    if not hasattr(g, "_location_repo"):
        g._location_repo = LocationRepository(get_db())
    return g._location_repo


def get_inventory_repo() -> InventoryRepository:
    if not hasattr(g, "_inventory_repo"):
        g._inventory_repo = InventoryRepository(get_db())
    return g._inventory_repo


def get_setting_repo() -> SettingRepository:
    if not hasattr(g, "_setting_repo"):
        g._setting_repo = SettingRepository(get_db())
    return g._setting_repo


def get_scan_service() -> ScanService:
    if not hasattr(g, "_scan_service"):
        g._scan_service = ScanService(
            kanban_repo=get_kanban_repo(),
            event_repo=get_event_repo(),
            inventory_repo=get_inventory_repo(),
        )
    return g._scan_service


def get_kanban_service() -> KanbanService:
    if not hasattr(g, "_kanban_service"):
        g._kanban_service = KanbanService(
            kanban_repo=get_kanban_repo(),
            event_repo=get_event_repo(),
            part_repo=get_part_repo(),
            setting_repo=get_setting_repo(),
            printer_factory=ZebraPrinter,
        )
    return g._kanban_service


def get_inventory_service() -> InventoryService:
    if not hasattr(g, "_inventory_service"):
        g._inventory_service = InventoryService(
            inventory_repo=get_inventory_repo(),
            event_repo=get_event_repo(),
            kanban_repo=get_kanban_repo(),
        )
    return g._inventory_service


def get_dashboard_service() -> DashboardService:
    if not hasattr(g, "_dashboard_service"):
        g._dashboard_service = DashboardService(
            kanban_repo=get_kanban_repo(),
            event_repo=get_event_repo(),
            part_repo=get_part_repo(),
            location_repo=get_location_repo(),
        )
    return g._dashboard_service


def get_report_service() -> ReportService:
    if not hasattr(g, "_report_service"):
        g._report_service = ReportService(
            event_repo=get_event_repo(),
            kanban_repo=get_kanban_repo(),
        )
    return g._report_service
