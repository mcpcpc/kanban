from quart import Blueprint, render_template, request

from kanban.db import get_db

bp = Blueprint("events", __name__, url_prefix="/events")


@bp.route("/")
async def history():
    """Show event history with filters."""
    db = get_db()
    
    search = request.args.get("search", "").strip()
    event_type = request.args.get("type", "").strip()
    kanban_id = request.args.get("kanban_id", "").strip()
    
    query = """
        SELECT 
            ke.id,
            ke.created_at,
            ke.quantity,
            ke.notes,
            ket.type as event_type,
            k.id as kanban_id,
            p.id as part_id,
            p.part_number as part_name,
            p.manufacturer,
            b.location as location_name
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        JOIN kanban k ON ke.kanban_id = k.id
        JOIN part p ON k.part_id = p.id
        JOIN location b ON k.location_id = b.id
        WHERE 1=1
    """
    params = []
    
    if search:
        query += " AND (p.part_number LIKE ? OR p.manufacturer LIKE ? OR b.location LIKE ? OR ke.notes LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param, search_param])
    
    if event_type:
        query += " AND ket.type = ?"
        params.append(event_type)
    
    if kanban_id:
        query += " AND k.id = ?"
        params.append(kanban_id)
    
    query += " ORDER BY ke.created_at DESC LIMIT 100"
    
    events = db.execute(query, params).fetchall()
    
    # Get event types for filter
    event_types = db.execute("SELECT * FROM kanban_event_type ORDER BY type").fetchall()
    
    return await render_template(
        "events/history.html",
        events=events,
        event_types=event_types,
        search=search,
        selected_type=event_type,
        kanban_id=kanban_id
    )


@bp.route("/export")
async def export():
    """Export events as CSV."""
    from quart import Response
    import csv
    import io
    
    db = get_db()
    
    event_type = request.args.get("type", "").strip()
    kanban_id = request.args.get("kanban_id", "").strip()
    
    query = """
        SELECT 
            ke.id,
            ke.created_at,
            ket.type as event_type,
            ke.quantity,
            ke.notes,
            k.id as kanban_id,
            p.part_number as part_name,
            p.manufacturer,
            b.location as location_name
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        JOIN kanban k ON ke.kanban_id = k.id
        JOIN part p ON k.part_id = p.id
        JOIN location b ON k.location_id = b.id
        WHERE 1=1
    """
    params = []
    
    if event_type:
        query += " AND ket.type = ?"
        params.append(event_type)
    
    if kanban_id:
        query += " AND k.id = ?"
        params.append(kanban_id)
    
    query += " ORDER BY ke.created_at DESC"
    
    events = db.execute(query, params).fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Event Type", "Quantity", "Notes", 
                     "Kanban ID", "Part Number", "Manufacturer", "Bin Location"])
    
    for event in events:
        writer.writerow([
            event["id"],
            event["created_at"].isoformat() if event["created_at"] else "",
            event["event_type"],
            event["quantity"] or "",
            event["notes"] or "",
            event["kanban_id"],
            event["part_name"],
            event["manufacturer"],
            event["location_name"]
        ])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=events.csv"}
    )
