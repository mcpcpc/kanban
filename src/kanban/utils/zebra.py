import socket
from logging import getLogger
from logging import debug
from logging import info
from logging import warning
from time import sleep

logger = getLogger(__name__)

DEFAULT_PORT = 9100
DEFAULT_TIMEOUT = 10.0


class ZebraPrinter:
    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT
    ):
        self.host = host
        self.port = port
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
        payload = zpl.encode("utf-8") if isinstance(zpl, str) else zpl

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

    def print(self, zpl: str | bytes) -> None:
        with self:
            self.send(zpl)

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
        return response.decode("utf-8", errors="replace")
