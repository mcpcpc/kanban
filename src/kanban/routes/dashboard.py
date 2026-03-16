from datetime import datetime, timedelta

from quart import Blueprint, render_template

from kanban.db import get_db

bp = Blueprint("dashboard", __name__)


@bp.route("/")
async def index():
    """Dashboard with system overview."""
    db = get_db()

    # Get counts
    total_parts = db.execute("SELECT COUNT(*) FROM part").fetchone()[0]
    total_bins = db.execute("SELECT COUNT(*) FROM bin").fetchone()[0]
    total_kanbans = db.execute("SELECT COUNT(*) FROM kanban WHERE is_active = 1").fetchone()[0]

    # Get recent events
    recent_events = db.execute("""
        SELECT 
            ke.id,
            ke.created_at,
            ke.quantity,
            ke.notes,
            ket.type as event_type,
            k.id as kanban_id,
            p.part_number as part_name,
            b.location as bin_location
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        JOIN kanban k ON ke.kanban_id = k.id
        JOIN part p ON k.part_id = p.id
        JOIN bin b ON k.bin_id = b.id
        ORDER BY ke.created_at DESC
        LIMIT 10
    """).fetchall()

    # Get pending signals (kanbans with more signals than restock_completes)
    pending_signals = db.execute("""
        SELECT * FROM (
            SELECT 
                k.id as kanban_id,
                p.part_number as part_name,
                p.manufacturer,
                b.location as bin_location,
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
            JOIN part p ON k.part_id = p.id
            JOIN bin b ON k.bin_id = b.id
            WHERE k.is_active = 1
        ) WHERE pending_count > 0
        ORDER BY signal_time ASC
    """).fetchall()

    # Convert signal_time strings to datetime (aggregates bypass PARSE_DECLTYPES)
    pending_signals = [
        {**dict(row), "signal_time": datetime.fromisoformat(row["signal_time"])}
        for row in pending_signals
    ]

    active_signals = len(pending_signals)

    # Sparkline trends for the last 30 days
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    # Kanban creation trend (for Active Kanbans card)
    daily_kanbans = db.execute("""
        SELECT date(created_at) as day, COUNT(*) as count
        FROM kanban
        WHERE created_at >= ?
        GROUP BY date(created_at)
        ORDER BY day
    """, (thirty_days_ago,)).fetchall()

    kanban_trend = []
    kanban_dict = {row['day']: row['count'] for row in daily_kanbans}
    for i in range(30):
        day = (datetime.now() - timedelta(days=29-i)).strftime('%Y-%m-%d')
        kanban_trend.append({'day': day, 'count': kanban_dict.get(day, 0)})
    kanban_max = max((p['count'] for p in kanban_trend), default=1) or 1

    # Parts creation trend
    daily_parts = db.execute("""
        SELECT date(created_at) as day, COUNT(*) as count
        FROM part
        WHERE created_at >= ?
        GROUP BY date(created_at)
        ORDER BY day
    """, (thirty_days_ago,)).fetchall()

    parts_trend = []
    parts_dict = {row['day']: row['count'] for row in daily_parts}
    for i in range(30):
        day = (datetime.now() - timedelta(days=29-i)).strftime('%Y-%m-%d')
        parts_trend.append({'day': day, 'count': parts_dict.get(day, 0)})
    parts_max = max((p['count'] for p in parts_trend), default=1) or 1

    # Bins creation trend
    daily_bins = db.execute("""
        SELECT date(created_at) as day, COUNT(*) as count
        FROM bin
        WHERE created_at >= ?
        GROUP BY date(created_at)
        ORDER BY day
    """, (thirty_days_ago,)).fetchall()

    bins_trend = []
    bins_dict = {row['day']: row['count'] for row in daily_bins}
    for i in range(30):
        day = (datetime.now() - timedelta(days=29-i)).strftime('%Y-%m-%d')
        bins_trend.append({'day': day, 'count': bins_dict.get(day, 0)})
    bins_max = max((p['count'] for p in bins_trend), default=1) or 1

    # Signals trend
    daily_signals = db.execute("""
        SELECT date(ke.created_at) as day, COUNT(*) as count
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        WHERE ket.type = 'signal' AND ke.created_at >= ?
        GROUP BY date(ke.created_at)
        ORDER BY day
    """, (thirty_days_ago,)).fetchall()

    signals_trend = []
    signals_dict = {row['day']: row['count'] for row in daily_signals}
    for i in range(30):
        day = (datetime.now() - timedelta(days=29-i)).strftime('%Y-%m-%d')
        signals_trend.append({'day': day, 'count': signals_dict.get(day, 0)})
    signals_max = max((p['count'] for p in signals_trend), default=1) or 1

    return await render_template(
        "dashboard/index.html",
        total_parts=total_parts,
        total_bins=total_bins,
        total_kanbans=total_kanbans,
        active_signals=active_signals,
        pending_signals=pending_signals,
        recent_events=recent_events,
        current_time=datetime.now(),
        kanban_trend=kanban_trend,
        kanban_max=kanban_max,
        parts_trend=parts_trend,
        parts_max=parts_max,
        bins_trend=bins_trend,
        bins_max=bins_max,
        signals_trend=signals_trend,
        signals_max=signals_max
    )
