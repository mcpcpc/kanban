import socket
import logging
from time import sleep
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PORT = 9100
DEFAULT_TIMEOUT = 5.0  # seconds


@dataclass
class LabelConfig:
    width_in: float
    height_in: float
    dpi: int
    gap_in: float = 0.12
    copies: int = 1
    darkness: int = 15
    print_speed: int = 4
    orientation: str = "N"
    label_top: int = 0
    label_shift: int = 0
    encoding: str = "utf-8"

    @property
    def dpmm(self) -> float:
        """Dots per millimetre derived from DPI (1 in = 25.4 mm)."""
        return self.dpi / 25.4

    @property
    def width_dots(self) -> int:
        """Label width expressed in printer dots."""
        return round(self.width_in * self.dpi)

    @property
    def height_dots(self) -> int:
        """Label height expressed in printer dots."""
        return round(self.height_in * self.dpi)

    @property
    def gap_dots(self) -> int:
        """Inter-label gap expressed in printer dots."""
        return round(self.gap_in * self.dpi)

    @property
    def width_mm(self) -> float:
        """Label width in millimetres."""
        return self.width_in * 25.4

    @property
    def height_mm(self) -> float:
        """Label height in millimetres."""
        return self.height_in * 25.4


class ZPLBuilder:
    def __init__(self, config: LabelConfig) -> None:
        self._cfg = config
        self._lines = []

    def start(self) -> "ZPLBuilder":
        c = self._cfg
        self._lines += [
            "^XA",
            f"^PW{c.width_dots}",
            f"^LL{c.height_dots}",
            f"^LH0,0",
            f"^LT{c.label_top}",
            f"^LS{c.label_shift}",
            f"^MD{c.darkness}",
            f"^PR{c.print_speed}",
            f"^PO{c.orientation}",
        ]
        return self

    def end(self) -> "ZPLBuilder":
        self._lines += [
            f"^PQ{self._cfg.copies}",
            "^XZ",
        ]
        return self

    def raw(self, zpl: str) -> "ZPLBuilder":
        self._lines.append(zpl)
        return self

    def text(
        self,
        x: int,
        y: int,
        text: str,
        font: str = "0",
        height: int = 30,
        width: Optional[int] = None,
    ) -> "ZPLBuilder":
        w = width or height
        self._lines += [
            f"^FO{x},{y}",
            f"^A{font}N,{height},{w}",
            f"^FD{text}^FS",
        ]
        return self

    def barcode_128(
        self,
        x: int,
        y: int,
        data: str,
        height: int = 100,
        line_width: int = 2,
        show_human_readable: bool = True,
    ) -> "ZPLBuilder":
        hr = "Y" if show_human_readable else "N"
        self._lines += [
            f"^FO{x},{y}",
            f"^BY{line_width}",
            f"^BCN,{height},{hr},N,N",
            f"^FD{data}^FS",
        ]
        return self

    def barcode_qr(
        self,
        x: int,
        y: int,
        data: str,
        magnification: int = 3,
        error_correction: str = "M",
    ) -> "ZPLBuilder":
        self._lines += [
            f"^FO{x},{y}",
            f"^BQN,2,{magnification},{error_correction}",
            f"^FDQA,{data}^FS",
        ]
        return self

    def line(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: str = "B",
    ) -> "ZPLBuilder":
        """Draw a filled rectangle / line using ^GB (Graphic Box)."""
        self._lines.append(f"^FO{x},{y}^GB{width},{height},1,{color}^FS")
        return self

    def image(self, x: int, y: int, zpl_image_data: str) -> "ZPLBuilder":
        """
        Place a pre-encoded GRF/Z64 image field.

        `zpl_image_data` should already be a valid ^GF or ~DG block.
        """
        self._lines += [f"^FO{x},{y}", zpl_image_data]
        return self

    def build(self) -> str:
        """Return the assembled ZPL string."""
        return "\n".join(self._lines)

    def encode(self) -> bytes:
        """Return the ZPL string encoded to bytes using the config encoding."""
        return self.build().encode(self._cfg.encoding)

    def reset(self) -> "ZPLBuilder":
        """Clear all accumulated ZPL commands."""
        self._lines.clear()
        return self
        

class ZebraPrinter:
    def __init__(
        self,
        host: str,
        config: LabelConfig,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self.config = config
        self.timeout = timeout
        self._sock = None

    def connect(self) -> None:
        if self._sock:
            logger.debug("Already connected to %s:%d", self.host, self.port)
            return
        logger.info("Connecting to %s:%d …", self.host, self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        self._sock = sock
        logger.info("Connected to %s:%d", self.host, self.port)

    def disconnect(self) -> None:
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._sock.close()
            self._sock = None
            logger.info("Disconnected from %s:%d", self.host, self.port)

    def is_connected(self) -> bool:
        return self._sock is not None

    def __enter__(self) -> "ZebraPrinter":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.disconnect()

    def send(self, zpl: str | bytes, retries: int = 2, retry_delay: float = 1.0) -> None:
        payload = zpl.encode(self.config.encoding) if isinstance(zpl, str) else zpl

        for attempt in range(retries + 1):
            try:
                if not self.is_connected():
                    self.connect()
                self._sock.sendall(payload)
                logger.info(
                    "Sent %d bytes to %s:%d", len(payload), self.host, self.port
                )
                return
            except (OSError, socket.error) as exc:
                logger.warning(
                    "Send attempt %d/%d failed: %s", attempt + 1, retries + 1, exc
                )
                self._sock = None  # Mark socket as dead
                if attempt < retries:
                    sleep(retry_delay)
                else:
                    raise

    def print_zpl(self, zpl: str | bytes) -> None:
        with self:
            self.send(zpl)

    def print_label(self, builder: ZPLBuilder) -> None:
        self.print_zpl(builder.encode())

    def query(self, command: str, buffer_size: int = 1024) -> str:
        response = b""
        with self:
            self.send(command)
            self._sock.settimeout(2.0)
            try:
                while True:
                    chunk = self._sock.recv(buffer_size)
                    if not chunk:
                        break
                    response += chunk
            except socket.timeout:
                pass  # Expected -- printer stops sending when done
        return response.decode(self.config.encoding, errors="replace")


def make_printer(
    host: str,
    width_in: float,
    height_in: float,
    dpi: int = 203,
    port: int = DEFAULT_PORT,
    **kwargs,
) -> ZebraPrinter:
    config = LabelConfig(
        width_in=width_in,
        height_in=height_in,
        dpi=dpi,
        **kwargs
    )
    return ZebraPrinter(
        host=host,
        port=port,
        config=config
    )
