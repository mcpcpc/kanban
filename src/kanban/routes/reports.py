from quart import Blueprint, render_template

from kanban.db import get_db

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
async def index():
    """Reports dashboard."""
    db = get_db()
    
    # Get overall stats
    total_events = db.execute("SELECT COUNT(*) FROM kanban_event").fetchone()[0]
    total_kanbans = db.execute("SELECT COUNT(*) FROM kanban WHERE is_active = 1").fetchone()[0]
    
    # Events by type
    events_by_type = db.execute("""
        SELECT ket.type, COUNT(*) as count
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        GROUP BY ket.id
        ORDER BY count DESC
    """).fetchall()
    
    # Most active kanbans
    active_kanbans = db.execute("""
        SELECT k.id, p.part_number as part_name, b.location as bin_location, COUNT(*) as event_count
        FROM kanban_event ke
        JOIN kanban k ON ke.kanban_id = k.id
        JOIN part p ON k.part_id = p.id
        JOIN bin b ON k.bin_id = b.id
        GROUP BY k.id
        ORDER BY event_count DESC
        LIMIT 10
    """).fetchall()
    
    # Calculate average cycle time (signal to restock_complete)
    cycle_times = db.execute("""
        SELECT 
            ke_signal.kanban_id,
            julianday(ke_complete.created_at) - julianday(ke_signal.created_at) as days
        FROM kanban_event ke_signal
        JOIN kanban_event_type ket_signal ON ke_signal.kanban_event_type = ket_signal.id
        JOIN kanban_event ke_complete ON ke_complete.kanban_id = ke_signal.kanban_id
        JOIN kanban_event_type ket_complete ON ke_complete.kanban_event_type = ket_complete.id
        WHERE ket_signal.type = 'signal'
        AND ket_complete.type = 'restock_complete'
        AND ke_complete.created_at > ke_signal.created_at
        AND NOT EXISTS (
            SELECT 1 FROM kanban_event ke2
            JOIN kanban_event_type ket2 ON ke2.kanban_event_type = ket2.id
            WHERE ke2.kanban_id = ke_signal.kanban_id
            AND ket2.type IN ('signal', 'restock_complete')
            AND ke2.created_at > ke_signal.created_at
            AND ke2.created_at < ke_complete.created_at
        )
    """).fetchall()
    
    avg_cycle_days = None
    if cycle_times:
        total_days = sum(row["days"] for row in cycle_times if row["days"])
        avg_cycle_days = total_days / len(cycle_times) if cycle_times else None
    
    return await render_template(
        "reports/index.html",
        total_events=total_events,
        total_kanbans=total_kanbans,
        events_by_type=events_by_type,
        active_kanbans=active_kanbans,
        avg_cycle_days=avg_cycle_days
    )
