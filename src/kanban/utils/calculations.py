"""Pure calculation helpers — no database or I/O dependencies.

These functions are intentionally free of side-effects so they can be
tested in isolation and reused from any layer.
"""

from math import ceil
from datetime import datetime, timedelta

from kanban.enums import InventoryStatus


def parse_barcode(barcode: str) -> int | None:
    """Extract a numeric kanban ID from a raw barcode string.

    Accepts either a ``K``-prefixed format (e.g. ``K000012``) or a plain
    integer string.  Returns *None* when the barcode cannot be parsed.
    """
    text = barcode.strip()
    if text.upper().startswith("K"):
        text = text[1:]
    try:
        return int(text)
    except ValueError:
        return None


def calculate_number_of_cards(
    estimated_daily_demand: float,
    lead_time_days: float,
    safety_lead_time_days: float,
    kanban_quantity: int,
) -> int:
    """Calculate how many kanban cards are needed.

    Formula: ``ceil((demand × (lead_time + safety_lt)) / container_qty)``
    Returns at least 1.
    """
    if kanban_quantity <= 0 or estimated_daily_demand <= 0:
        return 1
    total_lt = lead_time_days + safety_lead_time_days
    return max(1, ceil((estimated_daily_demand * total_lt) / kanban_quantity))


def build_30_day_trend(rows) -> tuple:
    """Fill a 30-day window from *rows* (each having ``day`` and ``count``).

    Returns ``(trend_list, max_value)`` where *trend_list* contains one
    ``{"day": ..., "count": ...}`` dict per day and *max_value* is the
    highest count (minimum 1, to avoid division-by-zero in sparklines).
    """
    lookup = {row["day"]: row["count"] for row in rows}
    trend = []
    for i in range(30):
        day = (datetime.now() - timedelta(days=29 - i)).strftime("%Y-%m-%d")
        trend.append({"day": day, "count": lookup.get(day, 0)})
    max_value = max((p["count"] for p in trend), default=1) or 1
    return trend, max_value


def determine_inventory_status(
    quantity_on_hand: float,
    total_reorder_point: float,
    days_of_supply: float | None,
    reorder_lead_time_days: float,
) -> InventoryStatus:
    """Classify inventory health."""
    if quantity_on_hand <= 0:
        return InventoryStatus.OUT
    if total_reorder_point > 0 and quantity_on_hand <= total_reorder_point:
        return InventoryStatus.LOW
    if days_of_supply is not None and days_of_supply <= reorder_lead_time_days:
        return InventoryStatus.WARNING
    return InventoryStatus.OK
