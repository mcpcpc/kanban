"""Service-layer classes that orchestrate repositories and business logic."""

from dataclasses import dataclass, field


@dataclass
class ServiceResult:
    """Lightweight container returned by service methods."""

    success: bool
    message: str
    category: str = "success"
    data: dict | None = field(default=None, repr=False)
