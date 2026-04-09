from asyncio import start_server
from asyncio import IncompleteReadError
from logging import info
from logging import exception

from quart import current_app

from kanban.db import get_db
from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.event import EventRepository
from kanban.repositories.inventory import InventoryRepository
from kanban.services.scan import ScanService


def is_datawedge_running() -> bool:
    """Check whether the DataWedge TCP server is currently serving."""
    server = getattr(current_app, "_datawedge_server", None)
    return server is not None and server.is_serving()


def _make_scan_service() -> ScanService:
    """Build a ScanService with a fresh DB connection (no request context)."""
    db = get_db()
    return ScanService(
        kanban_repo=KanbanRepository(db),
        event_repo=EventRepository(db),
        inventory_repo=InventoryRepository(db),
    )


async def save_scan(barcode: str) -> None:
    """Process a scanned barcode received via the DataWedge TCP socket."""
    service = _make_scan_service()
    service.process_datawedge_scan(barcode)


async def client_handler(reader, writer):
    addr = writer.get_extra_info("peername")
    info(f"DataWedge connected from {addr}")
    try:
        while True:
            raw = await reader.readline()
            if not raw:
                break  # Connection closed

            data = raw.decode("utf-8").strip()

            if not data:
                continue

            info(f"Scan received -- barcode: {data!r}")
            await save_scan(data)
    except IncompleteReadError:
        info(f"DataWedge client {addr} disconnected")
    except Exception as e:
        exception(f"Error handling DataWedge client {addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def start_datawedge_server(app, host: str, port: int) -> bool:
    if is_datawedge_running():
        info("DataWedge server already running")
        return True

    try:
        server = await start_server(client_handler, host, port)
        app._datawedge_server = server
        addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
        info(f"DataWedge TCP server listening on {addrs}")
        return True
    except OSError as e:
        exception(f"Failed to start DataWedge server: {e}")
        app._datawedge_server = None
        return False


async def stop_datawedge_server(app) -> bool:
    server = getattr(app, "_datawedge_server", None)

    if server is None or not server.is_serving():
        info("DataWedge server not running")
        return True

    try:
        server.close()
        await server.wait_closed()
        app._datawedge_server = None
        info("DataWedge server stopped")
        return True
    except Exception as e:
        exception(f"Error stopping DataWedge server: {e}")
        return False

def init_datawedge(app) -> None:
    """Register a ``before_serving`` hook that starts the DataWedge server."""

    @app.before_serving
    async def startup():
        host = app.config["DATAWEDGE_HOST"]
        port = app.config["DATAWEDGE_PORT"]
        await start_datawedge_server(app, host, port)
