from asyncio import start_server
from asyncio import IncompleteReadError
from logging import info
from logging import exception

from quart import current_app

from kanban.db import get_db


def is_datawedge_running() -> bool:
    server = getattr(current_app, "_datawedge_server", None)
    return server is not None and server.is_serving()


async def save_scan(barcode: str) -> None:
    kanban_id = None
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
    
    db = get_db()

    kanban = db.execute(
        """SELECT k.*, p.part_number as part_name, b.location as bin_location
           FROM kanban k
           JOIN part p ON k.part_id = p.id
           JOIN bin b ON k.bin_id = b.id
           WHERE k.id = ?""",
        [kanban_id]
    ).fetchone()

    if not kanban:
        info(f"Kanban not found: {barcode}")
        return

    if not kanban["is_active"]:
        info(f"Kanban is inactive: {kanban['part_name']} @ {kanban['bin_location']}")
        return

    open_signal_count = db.execute("""
        SELECT
            (SELECT COUNT(*) FROM kanban_event ke
             JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
             WHERE ke.kanban_id = ? AND ket.type = 'signal')
            -
            (SELECT COUNT(*) FROM kanban_event ke
             JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
             WHERE ke.kanban_id = ? AND ket.type = 'restock_complete')
        AS cnt
    """, [kanban_id, kanban_id]).fetchone()["cnt"]

    if open_signal_count >= kanban["number_of_cards"]:
        info(
            f"All {kanban['number_of_cards']} cards already signaled for "
            f"{kanban['part_name']} @ {kanban['bin_location']} — waiting for restock"
        )
        return

    event_type_row = db.execute(
        "SELECT id FROM kanban_event_type WHERE type = ?",
        ["signal"]
    ).fetchone()

    db.execute(
        """INSERT INTO kanban_event (kanban_id, kanban_event_type, quantity, notes)
           VALUES (?, ?, ?, ?)""",
        [kanban_id, event_type_row["id"], None, None]
    )

    db.execute("""
        UPDATE inventory
        SET quantity_on_hand = MAX(0, quantity_on_hand - ?),
            updated_at = CURRENT_TIMESTAMP
        WHERE part_id = ?
    """, [kanban["kanban_quantity"], kanban["part_id"]])

    db.commit()

    info(f"Signal recorded: {kanban['part_name']} @ {kanban['bin_location']}")


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
    @app.before_serving
    async def startup():
        await start_datawedge_server(app, "0.0.0.0", 58627)
