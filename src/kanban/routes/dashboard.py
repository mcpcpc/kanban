from datetime import datetime, timedelta

from quart import Blueprint, render_template

from kanban.db import get_db
from kanban.services import build_30_day_trend

bp = Blueprint("dashboard", __name__)


@bp.route("/")
async def index():
    """Dashboard with system overview."""
    db = get_db()

    total_parts = db.execute("SELECT COUNT(*) FROM part").fetchone()[0]
    total_locations = db.execute("SELECT COUNT(*) FROM location").fetchone()[0]
    total_kanbans = db.execute(
        "SELECT COUNT(*) FROM kanban WHERE is_active = 1"
    ).fetchone()[0]

    recent_events = db.execute("""
        SELECT
            ke.id,
            ke.created_at,
            ke.quantity,
            ke.notes,
            ket.type AS event_type,
            k.id   AS kanban_id,
            p.part_number AS part_name,
            b.location    AS location_name
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        JOIN kanban k   ON ke.kanban_id  = k.id
        JOIN part p     ON k.part_id     = p.id
        JOIN location b ON k.location_id = b.id
        ORDER BY ke.created_at DESC
        LIMIT 10
    """).fetchall()

    pending_signals = db.execute("""
        SELECT * FROM (
            SELECT
                k.id AS kanban_id,
                p.part_number AS part_name,
                p.manufacturer,
                b.location AS location_name,
                (
                    SELECT COUNT(*) FROM kanban_event ke
                    JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                    WHERE ke.kanban_id = k.id AND ket.type = 'signal'
                ) - (
                    SELECT COUNT(*) FROM kanban_event ke
                    JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                    WHERE ke.kanban_id = k.id AND ket.type = 'restock_complete'
                ) AS pending_count,
                (
                    SELECT MAX(ke.created_at) FROM kanban_event ke
                    JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                    WHERE ke.kanban_id = k.id AND ket.type = 'signal'
                ) AS signal_time
            FROM kanban k
            JOIN part p     ON k.part_id     = p.id
            JOIN location b ON k.location_id = b.id
            WHERE k.is_active = 1
        ) WHERE pending_count > 0
        ORDER BY signal_time ASC
    """).fetchall()

    # Aggregate functions bypass PARSE_DECLTYPES — convert manually.
    pending_signals = [
        {**dict(row), "signal_time": datetime.fromisoformat(row["signal_time"])}
        for row in pending_signals
    ]

    active_signals = len(pending_signals)

    # --- Sparkline trends (last 30 days) ---
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    kanban_trend, kanban_max = build_30_day_trend(db.execute("""
        SELECT date(created_at) AS day, COUNT(*) AS count
        FROM kanban WHERE created_at >= ?
        GROUP BY date(created_at) ORDER BY day
    """, (thirty_days_ago,)).fetchall())

    parts_trend, parts_max = build_30_day_trend(db.execute("""
        SELECT date(created_at) AS day, COUNT(*) AS count
        FROM part WHERE created_at >= ?
        GROUP BY date(created_at) ORDER BY day
    """, (thirty_days_ago,)).fetchall())

    locations_trend, locations_max = build_30_day_trend(db.execute("""
        SELECT date(created_at) AS day, COUNT(*) AS count
        FROM location WHERE created_at >= ?
        GROUP BY date(created_at) ORDER BY day
    """, (thirty_days_ago,)).fetchall())

    signals_trend, signals_max = build_30_day_trend(db.execute("""
        SELECT date(ke.created_at) AS day, COUNT(*) AS count
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        WHERE ket.type = 'signal' AND ke.created_at >= ?
        GROUP BY date(ke.created_at) ORDER BY day
    """, (thirty_days_ago,)).fetchall())

    return await render_template(
        "dashboard/index.html",
        total_parts=total_parts,
        total_locations=total_locations,
        total_kanbans=total_kanbans,
        active_signals=active_signals,
        pending_signals=pending_signals,
        recent_events=recent_events,
        current_time=datetime.now(),
        kanban_trend=kanban_trend,
        kanban_max=kanban_max,
        parts_trend=parts_trend,
        parts_max=parts_max,
        locations_trend=locations_trend,
        locations_max=locations_max,
        signals_trend=signals_trend,
        signals_max=signals_max,
    )
