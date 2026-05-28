"""Structural typing protocols for dependency inversion."""

from typing import Protocol


class Printer(Protocol):
    """Narrow interface for sending ZPL to a label printer."""

    def print(self, zpl: str | bytes) -> None: ...
