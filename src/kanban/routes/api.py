from quart import Blueprint, jsonify, request

from kanban.db import get_db
from kanban.oauth import authorize

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/kanbans")
@authorize
async def list_kanbans():
    """List kanbans with status."""
    db = get_db()
    
    kanbans = db.execute("""
        SELECT k.*, p.part_number as part_name, p.manufacturer, 
               p.reorder_lead_time_days,
               b.location as bin_location,
               CAST(k.estimated_daily_demand * (p.reorder_lead_time_days + k.safety_lead_time_days) AS INTEGER) as reorder_point
        FROM kanban k
        JOIN part p ON k.part_id = p.id
        JOIN bin b ON k.bin_id = b.id
        WHERE k.is_active = 1
        ORDER BY p.part_number
    """).fetchall()
    
    result = []
    for k in kanbans:
        result.append({
            "id": k["id"],
            "part_name": k["part_name"],
            "manufacturer": k["manufacturer"],
            "bin_location": k["bin_location"],
            "kanban_quantity": k["kanban_quantity"],
            "reorder_point": k["reorder_point"],
            "safety_lead_time_days": k["safety_lead_time_days"],
            "estimated_daily_demand": k["estimated_daily_demand"],
            "number_of_cards": k["number_of_cards"],
            "is_active": bool(k["is_active"])
        })
    
    return jsonify(result)


@bp.route("/kanbans/<int:id>")
@authorize
async def get_kanban(id):
    """Get kanban detail with recent events."""
    db = get_db()
    
    kanban = db.execute("""
        SELECT k.*, p.part_number as part_name, p.manufacturer, 
               p.reorder_lead_time_days,
               b.location as bin_location,
               CAST(k.estimated_daily_demand * (p.reorder_lead_time_days + k.safety_lead_time_days) AS INTEGER) as reorder_point
        FROM kanban k
        JOIN part p ON k.part_id = p.id
        JOIN bin b ON k.bin_id = b.id
        WHERE k.id = ?
    """, [id]).fetchone()
    
    if not kanban:
        return jsonify({"error": "Kanban not found"}), 404
    
    events = db.execute("""
        SELECT ke.*, ket.type as event_type
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        WHERE ke.kanban_id = ?
        ORDER BY ke.created_at DESC
        LIMIT 20
    """, [id]).fetchall()
    
    return jsonify({
        "id": kanban["id"],
        "part_name": kanban["part_name"],
        "manufacturer": kanban["manufacturer"],
        "bin_location": kanban["bin_location"],
        "kanban_quantity": kanban["kanban_quantity"],
        "reorder_point": kanban["reorder_point"],
        "safety_lead_time_days": kanban["safety_lead_time_days"],
        "estimated_daily_demand": kanban["estimated_daily_demand"],
        "number_of_cards": kanban["number_of_cards"],
        "is_active": bool(kanban["is_active"]),
        "events": [
            {
                "id": e["id"],
                "event_type": e["event_type"],
                "quantity": e["quantity"],
                "notes": e["notes"],
                "created_at": e["created_at"].isoformat() if e["created_at"] else None
            }
            for e in events
        ]
    })


@bp.route("/events", methods=["POST"])
@authorize
async def record_event():
    """Record a kanban event."""
    db = get_db()
    data = await request.get_json()
    
    kanban_id = data.get("kanban_id")
    event_type = data.get("event_type")
    quantity = data.get("quantity")
    notes = data.get("notes")
    
    if not kanban_id or not event_type:
        return jsonify({"error": "kanban_id and event_type are required"}), 400
    
    # Verify kanban exists
    kanban = db.execute("SELECT id FROM kanban WHERE id = ?", [kanban_id]).fetchone()
    if not kanban:
        return jsonify({"error": "Kanban not found"}), 404
    
    # Get event type ID
    event_type_row = db.execute(
        "SELECT id FROM kanban_event_type WHERE type = ?",
        [event_type]
    ).fetchone()
    
    if not event_type_row:
        return jsonify({"error": f"Invalid event_type: {event_type}"}), 400
    
    # Validate signal: prevent multiple active signals for same kanban
    if event_type == "signal":
        active_signal = db.execute("""
            SELECT ke.created_at FROM kanban_event ke
            JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
            WHERE ke.kanban_id = ?
            AND ket.type = 'signal'
            AND NOT EXISTS (
                SELECT 1 FROM kanban_event ke2
                JOIN kanban_event_type ket2 ON ke2.kanban_event_type = ket2.id
                WHERE ke2.kanban_id = ke.kanban_id
                AND ket2.type = 'restock_complete'
                AND ke2.created_at > ke.created_at
            )
            LIMIT 1
        """, [kanban_id]).fetchone()
        
        if active_signal:
            return jsonify({"error": "Active signal already exists for this kanban — waiting for restock"}), 409
    
    cursor = db.execute(
        """INSERT INTO kanban_event (kanban_id, kanban_event_type, quantity, notes)
           VALUES (?, ?, ?, ?)""",
        [kanban_id, event_type_row["id"], quantity, notes]
    )
    db.commit()
    
    return jsonify({
        "id": cursor.lastrowid,
        "kanban_id": kanban_id,
        "event_type": event_type,
        "quantity": quantity,
        "notes": notes
    }), 201


@bp.route("/health")
@authorize
async def health():
    """System health summary."""
    db = get_db()
    
    total_kanbans = db.execute("SELECT COUNT(*) FROM kanban WHERE is_active = 1").fetchone()[0]
    total_parts = db.execute("SELECT COUNT(*) FROM part").fetchone()[0]
    total_bins = db.execute("SELECT COUNT(*) FROM bin").fetchone()[0]
    total_events = db.execute("SELECT COUNT(*) FROM kanban_event").fetchone()[0]
    
    # Count kanbans with pending signals (more signals than restock_completes)
    pending_signals = db.execute("""
        SELECT COUNT(*) FROM (
            SELECT k.id
            FROM kanban k
            WHERE k.is_active = 1
            AND (
                SELECT COUNT(*) FROM kanban_event ke
                JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                WHERE ke.kanban_id = k.id AND ket.type = 'signal'
            ) > (
                SELECT COUNT(*) FROM kanban_event ke
                JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                WHERE ke.kanban_id = k.id AND ket.type = 'restock_complete'
            )
        )
    """).fetchone()[0]
    
    return jsonify({
        "total_kanbans": total_kanbans,
        "total_parts": total_parts,
        "total_bins": total_bins,
        "total_events": total_events,
        "pending_signals": pending_signals,
        "health": {
            "healthy": total_kanbans - pending_signals,
            "warning": pending_signals,
            "critical": 0
        }
    })


@bp.route("/metrics")
@authorize
async def metrics():
    """Performance metrics."""
    db = get_db()
    
    # Events in last 7 days by type
    events_7d = db.execute("""
        SELECT ket.type, COUNT(*) as count
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        WHERE ke.created_at >= datetime('now', '-7 days')
        GROUP BY ket.id
    """).fetchall()
    
    # Average cycle time
    cycle_times = db.execute("""
        SELECT AVG(julianday(ke_complete.created_at) - julianday(ke_signal.created_at)) as avg_days
        FROM kanban_event ke_signal
        JOIN kanban_event_type ket_signal ON ke_signal.kanban_event_type = ket_signal.id
        JOIN kanban_event ke_complete ON ke_complete.kanban_id = ke_signal.kanban_id
        JOIN kanban_event_type ket_complete ON ke_complete.kanban_event_type = ket_complete.id
        WHERE ket_signal.type = 'signal'
        AND ket_complete.type = 'restock_complete'
        AND ke_complete.created_at > ke_signal.created_at
    """).fetchone()
    
    return jsonify({
        "events_7d": {row["type"]: row["count"] for row in events_7d},
        "avg_cycle_time_days": cycle_times["avg_days"] if cycle_times else None
    })


@bp.route("/kanbans/<int:id>/suggest-reorder-point")
@authorize
async def suggest_reorder_point(id):
    """Calculate reorder point based on estimated demand, lead time, and safety stock.
    
    Formula: Reorder Point = (Estimated Daily Demand × Lead Time) + Safety Stock
    """
    db = get_db()
    
    kanban = db.execute("""
        SELECT k.*, p.reorder_lead_time_days
        FROM kanban k
        JOIN part p ON k.part_id = p.id
        WHERE k.id = ?
    """, [id]).fetchone()
    
    if not kanban:
        return jsonify({"error": "Kanban not found"}), 404
    
    estimated_daily_demand = kanban["estimated_daily_demand"]
    lead_time = kanban["reorder_lead_time_days"]
    safety_lead_time = kanban["safety_lead_time_days"]
    
    # Formula: D × (LT + Safety LT)
    reorder_point = int(estimated_daily_demand * (lead_time + safety_lead_time))
    
    return jsonify({
        "kanban_id": id,
        "estimated_daily_demand": estimated_daily_demand,
        "lead_time_days": lead_time,
        "safety_lead_time_days": safety_lead_time,
        "reorder_point": reorder_point,
        "formula": "estimated_daily_demand × (lead_time + safety_lead_time)"
    })
