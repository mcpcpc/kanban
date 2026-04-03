from asyncio import start_server
from asyncio import IncompleteReadError
from json import loads
from json import JSONDecodeError
from logging import info
from logging import exception
from logging import getLogger

from kanban.db import get_db

logger = getLogger(__name__)


def is_datawedge_running() -> bool:
    server = getattr(current_app, "_datawedge_server", None)
    return server is not None and server.is_serving()


async def save_scan(barcode: str) -> None:
    if barcode.upper().startswith("K"):
        try:
            kanban_id = int(barcode[1:])
        except ValueError:
            pass
    else:
        try:
            kanban_id = int(barcode)
        except ValueError:
            pass
    
    if not kanban_id:
        info(f"Invalid barcode format: {barcode}")
        return
    
    print(kanban_id)


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
    host = app.config["DATAWEDGE_HOST"]
    port = app.config["DATAWEDGE_PORT"]

    @app.before_serving
    async def startup():
        await start_datawedge_server(app, host, port)
