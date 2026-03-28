from asyncio import start_server
from asyncio import IncompleteReadError
from json import loads
from json import JSONDecodeError
from logging import info
from logging import exception
from logging import getLogger

from kanban.db import get_db

logger = getLogger(__name__)


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


async def handle_datawedge_client(reader, writer):
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


async def start_datawedge_server(host, port):
    server = await start_server(handle_datawedge_client, host, port)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    info(f"DataWedge TCP server listening on {addrs}")
    async with server:
        await server.serve_forever()

def init_datawedge(app) -> None:
    host = app.config["DATAWEDGE_HOST"]
    port = app.config["DATAWEDGE_PORT"]

    @app.before_serving
    async def startup():
        app.add_background_task(
            start_datawedge_server,
            host=host,
            port=port
        )
