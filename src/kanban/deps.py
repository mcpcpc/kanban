"""Request-scoped dependency injection helpers."""

from sqlite3 import Connection

from quart import g

from kanban.db import get_db
from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.event import EventRepository
from kanban.repositories.part import PartRepository
from kanban.repositories.location import LocationRepository
from kanban.repositories.inventory import InventoryRepository
from kanban.repositories.setting import SettingRepository
from kanban.repositories.user import UserRepository
from kanban.services.scan import ScanService
from kanban.services.kanban import KanbanService
from kanban.services.inventory import InventoryService
from kanban.services.dashboard import DashboardService
from kanban.services.report import ReportService
from kanban.services.print import PrintService
from kanban.services.part import PartService
from kanban.services.location import LocationService
from kanban.services.user import UserService
from kanban.zebra import ZebraPrinter


def _g(key, factory):
    if not hasattr(g, key):
        setattr(g, key, factory())
    return getattr(g, key)


def get_kanban_repo() -> KanbanRepository:
    return _g("_kanban_repo", lambda: KanbanRepository(get_db()))

def get_event_repo() -> EventRepository:
    return _g("_event_repo", lambda: EventRepository(get_db()))

def get_part_repo() -> PartRepository:
    return _g("_part_repo", lambda: PartRepository(get_db()))

def get_location_repo() -> LocationRepository:
    return _g("_location_repo", lambda: LocationRepository(get_db()))

def get_inventory_repo() -> InventoryRepository:
    return _g("_inventory_repo", lambda: InventoryRepository(get_db()))

def get_setting_repo() -> SettingRepository:
    return _g("_setting_repo", lambda: SettingRepository(get_db()))


def make_scan_service(db: Connection) -> ScanService:
    """Create a ScanService from a database connection.

    Usable both inside (via ``get_scan_service``) and outside
    (DataWedge TCP handler) a request context.
    """
    return ScanService(
        kanban_repo=KanbanRepository(db),
        event_repo=EventRepository(db),
        inventory_repo=InventoryRepository(db),
    )


def get_scan_service() -> ScanService:
    return _g("_scan_service", lambda: make_scan_service(get_db()))

def get_kanban_service() -> KanbanService:
    return _g("_kanban_service", lambda: KanbanService(
        kanban_repo=get_kanban_repo(),
        event_repo=get_event_repo(),
        part_repo=get_part_repo(),
        location_repo=get_location_repo(),
    ))

def get_print_service() -> PrintService:
    return _g("_print_service", lambda: PrintService(
        kanban_repo=get_kanban_repo(),
        setting_repo=get_setting_repo(),
        printer_factory=ZebraPrinter,
    ))

def get_part_service() -> PartService:
    return _g("_part_service", lambda: PartService(
        part_repo=get_part_repo(),
        kanban_repo=get_kanban_repo(),
    ))

def get_location_service() -> LocationService:
    return _g("_location_service", lambda: LocationService(
        location_repo=get_location_repo(),
        kanban_repo=get_kanban_repo(),
    ))

def get_inventory_service() -> InventoryService:
    return _g("_inventory_service", lambda: InventoryService(
        inventory_repo=get_inventory_repo(),
        event_repo=get_event_repo(),
        kanban_repo=get_kanban_repo(),
    ))

def get_dashboard_service() -> DashboardService:
    return _g("_dashboard_service", lambda: DashboardService(
        kanban_repo=get_kanban_repo(),
        event_repo=get_event_repo(),
        part_repo=get_part_repo(),
        location_repo=get_location_repo(),
    ))

def get_report_service() -> ReportService:
    return _g("_report_service", lambda: ReportService(
        event_repo=get_event_repo(),
        kanban_repo=get_kanban_repo(),
    ))

def get_user_repo() -> UserRepository:
    return _g("_user_repo", lambda: UserRepository(get_db()))

def get_user_service() -> UserService:
    return _g("_user_service", lambda: UserService(get_user_repo()))
