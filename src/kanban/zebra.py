from socket import AF_INET
from socket import SOCK_STREAM
from socket import SHUT_RDWR
from socket import socket
from logging import debug
from logging import info
from logging import warning
from time import sleep

class ZebraPrinter:
    def __init__(self, host: str, port: int, timeout: float):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None

    def connect(self) -> None:
        if self.sock:
            debug("Already connected to %s:%d", self.host, self.port)
            return
        info("Connecting to %s:%d …", self.host, self.port)
        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        self.sock = sock
        info("Connected to %s:%d", self.host, self.port)

    def disconnect(self) -> None:
        if self.sock:
            try:
                self.sock.shutdown(SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None
            info("Disconnected from %s:%d", self.host, self.port)

    def is_connected(self) -> bool:
        return self.sock is not None

    def __enter__(self) -> "ZebraPrinter":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.disconnect()

    def send(self, zpl: str | bytes, retries: int = 2, retry_delay: float = 1.0) -> None:
        payload = zpl.encode("utf-8") if isinstance(zpl, str) else zpl

        for attempt in range(retries + 1):
            try:
                if not self.is_connected():
                    self.connect()
                self.sock.sendall(payload)
                info("Sent %d bytes to %s:%d", len(payload), self.host, self.port)
                return
            except OSError as exc:
                warning(
                    "Send attempt %d/%d failed: %s", attempt + 1, retries + 1, exc
                )
                self.sock = None  # Mark socket as dead
                if attempt < retries:
                    sleep(retry_delay)
                else:
                    raise

    def print(self, zpl: str | bytes) -> None:
        with self:
            self.send(zpl)


class KanbanLabelTemplate:
    def __init__(self,
        id: int,
        location_name: str,
        part_number: str,
        manufacturer: str,
        part_description: str,
        uom_abbr: str,
        reorder_point: int,
        kanban_quantity: int,
        number_of_cards: int,
        **kwargs
    ) -> None:
        self.id = id
        self.location_name = location_name
        self.part_number = part_number
        self.manufacturer = manufacturer
        self.part_description = part_description
        self.uom_abbr = uom_abbr
        self.reorder_point = reorder_point
        self.kanban_quantity = kanban_quantity
        self.number_of_cards = number_of_cards

    def render(self, card_number: int, template: str) -> str:
        return template.format(
            id=self.id,
            location_name=self.location_name,
            part_number=self.part_number,
            manufacturer=self.manufacturer,
            part_description=self.part_description,
            uom_abbr=self.uom_abbr,
            reorder_point=self.reorder_point,
            kanban_quantity=self.kanban_quantity,
            number_of_cards=self.number_of_cards,
            card_number=card_number,
        )
