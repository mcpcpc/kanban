import socket
from dataclasses import dataclass, field
from enum import Enum
from logging import getLogger, debug, info, warning
from time import sleep
from typing import Optional

logger = getLogger(__name__)


class MediaType(Enum):
    WEB = "Y"         # Die-cut labels separated by gaps (^MNY). Requires length + gap.
    BLACK_MARK = "M"  # Labels with a black reflective mark (^MNM). Requires length + gap (mark height).
    NOTCH = "N"       # Labels with a notch or hole (^MNN). Requires length + gap.
    CONTINUOUS = "C"  # Continuous roll with no gaps or marks (^MNC). Length and gap are not used.

    @property
    def requires_length(self) -> bool:
        return self != MediaType.CONTINUOUS

    @property
    def requires_gap(self) -> bool:
        return self != MediaType.CONTINUOUS


@dataclass
class LabelConfig:
    width_in: float
    dpi: int
    media_type: MediaType = MediaType.WEB
    length_in: Optional[float] = None
    gap_in: Optional[float] = None
    copies: int = 1
    darkness: int = 15
    print_speed: int = 4
    orientation: str = "N"
    label_top: int = 0
    label_shift: int = 0
    encoding: str = "utf-8"

    def __post_init__(self) -> None:
        if self.media_type.requires_length and self.length_in is None:
            raise ValueError(
                f"MediaType.{self.media_type.name} requires 'length_in' to be set."
            )
        if self.media_type.requires_gap and self.gap_in is None:
            raise ValueError(
                f"MediaType.{self.media_type.name} requires 'gap_in' to be set."
            )
        if not self.media_type.requires_length and self.length_in is not None:
            raise ValueError(
                f"MediaType.{self.media_type.name} is continuous -- 'length_in' should not be set."
            )
        if not self.media_type.requires_gap and self.gap_in is not None:
            raise ValueError(
                f"MediaType.{self.media_type.name} is continuous -- 'gap_in' should not be set."
            )

    @property
    def dpmm(self) -> float:
        return self.dpi / 25.4

    @property
    def width_dots(self) -> int:
        return round(self.width_in * self.dpi)

    @property
    def length_dots(self) -> Optional[int]:
        return round(self.length_in * self.dpi) if self.length_in is not None else None

    @property
    def gap_dots(self) -> Optional[int]:
        return round(self.gap_in * self.dpi) if self.gap_in is not None else None

    @property
    def width_mm(self) -> float:
        return self.width_in * 25.4

    @property
    def length_mm(self) -> Optional[float]:
        return self.length_in * 25.4 if self.length_in is not None else None


class ZPLBuilder:
    def __init__(self, config: LabelConfig):
        self._cfg = config
        self._lines: list[str] = []

    def start(self) -> "ZPLBuilder":
        c = self._cfg
        self._lines += [
            "^XA",
            f"^PW{c.width_dots}",
            f"^MN{c.media_type.value}",
        ]
        if c.length_dots is not None:
            self._lines.append(f"^LL{c.length_dots + (c.gap_dots or 0)}")  # Label length inc. gap
        self._lines += [
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

    def textblock(
        self,
        x: int,
        y: int,
        text: str,
        width: int,
        max_lines: int = 1,
        font: str = "0",
        font_height: int = 30,
        font_width: Optional[int] = None,
        line_spacing: int = 0,
        justification: str = "L",
    ) -> "ZPLBuilder":
        fw = font_width or font_height
        self._lines += [
            f"^FO{x},{y}",
            f"^A{font}N,{font_height},{fw}",
            f"^TB{justification},{width},{font_height * max_lines + line_spacing * (max_lines - 1)}",
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
        self._lines.append(f"^FO{x},{y}^GB{width},{height},1,{color}^FS")
        return self

    def image(self, x: int, y: int, zpl_image_data: str) -> "ZPLBuilder":
        self._lines += [f"^FO{x},{y}", zpl_image_data]
        return self

    def build(self) -> str:
        return "\n".join(self._lines)

    def encode(self) -> bytes:
        return self.build().encode(self._cfg.encoding)

    def reset(self) -> "ZPLBuilder":
        self._lines.clear()
        return self


class ZebraPrinter:
    DEFAULT_PORT = 9100

    def __init__(
        self,
        host: str,
        config: LabelConfig,
        port: int = DEFAULT_PORT,
        timeout: float = 10.0,
    ):
        self.host = host
        self.port = port
        self.config = config
        self.timeout = timeout
        self.sock = None

    def connect(self) -> None:
        if self.sock:
            debug("Already connected to %s:%d", self.host, self.port)
            return
        info("Connecting to %s:%d …", self.host, self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        self.sock = sock
        info("Connected to %s:%d", self.host, self.port)

    def disconnect(self) -> None:
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
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
        payload = zpl.encode(self.config.encoding) if isinstance(zpl, str) else zpl

        for attempt in range(retries + 1):
            try:
                if not self.is_connected():
                    self.connect()
                self.sock.sendall(payload)
                info("Sent %d bytes to %s:%d", len(payload), self.host, self.port)
                return
            except (OSError, socket.error) as exc:
                warning(
                    "Send attempt %d/%d failed: %s", attempt + 1, retries + 1, exc
                )
                self.sock = None  # Mark socket as dead
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
            self.sock.settimeout(2.0)
            try:
                while True:
                    chunk = self.sock.recv(buffer_size)
                    if not chunk:
                        break
                    response += chunk
            except socket.timeout:
                pass  # Expected -- printer stops sending when done
        return response.decode(self.config.encoding, errors="replace")


def make_printer(
    host: str,
    width_in: float,
    length_in: float,
    dpi: int = 203,
    port: int = ZebraPrinter.DEFAULT_PORT,
    **label_kwargs,
) -> ZebraPrinter:
    config = LabelConfig(width_in=width_in, length_in=length_in, dpi=dpi, **label_kwargs)
    return ZebraPrinter(host=host, port=port, config=config)
