from asyncio import start_server
from asyncio import IncompleteReadError
from json import loads
from json import JSONDecodeError
from logger import info
from logger import exception


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
            await save_scan(barcode, barcode_type)
    except IncompleteReadError:
        info(f"DataWedge client {addr} disconnected")
    except Exception as e:
        exception(f"Error handling DataWedge client {addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def start_datawedge_server():
    server = await start_server(handle_datawedge_client, "0.0.0.0", TCP_PORT)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    info(f"DataWedge TCP server listening on {addrs}")
    async with server:
        await server.serve_forever()

def init_datawedge(app) -> None:
    app.add_background_task(start_datawedge_server)
