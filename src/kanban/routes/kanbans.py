import math

from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.db import get_db
from kanban.oauth import authorize
from kanban.utils.zebra import ZebraPrinter

bp = Blueprint("kanbans", __name__, url_prefix="/kanbans")


@bp.route("/")
@authorize
async def list():
    """List all kanbans."""
    db = get_db()
    
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    
    query = """
        SELECT k.*, p.part_number as part_name, p.manufacturer, 
               p.reorder_lead_time_days,
               b.location as bin_location,
               CAST(k.estimated_daily_demand * (p.reorder_lead_time_days + k.safety_lead_time_days) AS INTEGER) as reorder_point
        FROM kanban k
        JOIN part p ON k.part_id = p.id
        JOIN bin b ON k.bin_id = b.id
        WHERE 1=1
    """
    params = []
    
    if search:
        query += " AND (p.part_number LIKE ? OR p.manufacturer LIKE ? OR b.location LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
    
    if status == "active":
        query += " AND k.is_active = 1"
    elif status == "inactive":
        query += " AND k.is_active = 0"
    
    query += " ORDER BY p.part_number, b.location"
    
    kanbans = db.execute(query, params).fetchall()
    
    return await render_template(
        "kanbans/list.html",
        kanbans=kanbans,
        search=search,
        selected_status=status
    )


@bp.route("/new")
@authorize
async def new():
    """Show new kanban form."""
    db = get_db()
    parts = db.execute("SELECT * FROM part ORDER BY part_number").fetchall()
    bins = db.execute("SELECT * FROM bin ORDER BY location").fetchall()
    selected_bin_id = request.args.get("bin_id", type=int)
    selected_part_id = request.args.get("part_id", type=int)
    return await render_template("kanbans/form.html", kanban=None, parts=parts, bins=bins, selected_bin_id=selected_bin_id, selected_part_id=selected_part_id)


@bp.route("/", methods=["POST"])
@authorize
async def create():
    """Create a new kanban."""
    db = get_db()
    form = await request.form
    
    part_id = form.get("part_id")
    bin_id = form.get("bin_id")
    kanban_quantity = form.get("kanban_quantity", "100")
    safety_lead_time_days = form.get("safety_lead_time_days", "0")
    estimated_daily_demand = form.get("estimated_daily_demand", "0")
    is_active = form.get("is_active") == "on"
    
    if not part_id or not bin_id:
        await flash("Part and Location are required.", "danger")
        return redirect(url_for("kanbans.new"))
    
    try:
        kanban_quantity = int(kanban_quantity) if kanban_quantity else 100
        safety_lead_time_days = float(safety_lead_time_days) if safety_lead_time_days else 0
        estimated_daily_demand = float(estimated_daily_demand) if estimated_daily_demand else 0
    except ValueError:
        await flash("Invalid quantity values.", "danger")
        return redirect(url_for("kanbans.new"))
    
    # Calculate number of cards: ceil((Demand × (Lead Time + Safety LT)) / Container Qty)
    part = db.execute("SELECT reorder_lead_time_days FROM part WHERE id = ?", [part_id]).fetchone()
    lead_time = part["reorder_lead_time_days"] if part else 7
    total_lt = lead_time + safety_lead_time_days
    if kanban_quantity > 0 and estimated_daily_demand > 0:
        number_of_cards = max(1, math.ceil((estimated_daily_demand * total_lt) / kanban_quantity))
    else:
        number_of_cards = 1
    
    cursor = db.execute(
        """INSERT INTO kanban (part_id, bin_id, kanban_quantity,
           safety_lead_time_days, estimated_daily_demand, number_of_cards, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [part_id, bin_id, kanban_quantity,
         safety_lead_time_days, estimated_daily_demand, number_of_cards, 1 if is_active else 0]
    )
    db.commit()
    
    await flash("Kanban created successfully.", "success")
    return redirect(url_for("kanbans.detail", id=cursor.lastrowid))


@bp.route("/<int:id>")
@authorize
async def detail(id):
    """Show kanban details."""
    db = get_db()
    kanban = db.execute(
        """SELECT k.*, p.part_number as part_name, p.manufacturer, p.description as part_description,
                  p.reorder_lead_time_days,
                  b.location as bin_location,
                  u.name as uom_name, u.abbreviation as uom_abbr,
                  CAST(k.estimated_daily_demand * (p.reorder_lead_time_days + k.safety_lead_time_days) AS INTEGER) as reorder_point
           FROM kanban k
           JOIN part p ON k.part_id = p.id
           JOIN bin b ON k.bin_id = b.id
           JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
           WHERE k.id = ?""",
        [id]
    ).fetchone()
    
    if not kanban:
        await flash("Kanban not found.", "danger")
        return redirect(url_for("kanbans.list"))
    
    # Get recent events for this kanban
    events = db.execute(
        """SELECT ke.*, ket.type as event_type
           FROM kanban_event ke
           JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
           WHERE ke.kanban_id = ?
           ORDER BY ke.created_at DESC
           LIMIT 20""",
        [id]
    ).fetchall()
    
    return await render_template("kanbans/detail.html", kanban=kanban, events=events)


@bp.route("/<int:id>/edit")
@authorize
async def edit(id):
    """Show edit kanban form."""
    db = get_db()
    kanban = db.execute("""
        SELECT k.*, p.reorder_lead_time_days as lead_time_days
        FROM kanban k
        JOIN part p ON k.part_id = p.id
        WHERE k.id = ?
    """, [id]).fetchone()
    
    if not kanban:
        await flash("Kanban not found.", "danger")
        return redirect(url_for("kanbans.list"))
    
    parts = db.execute("SELECT * FROM part ORDER BY part_number").fetchall()
    bins = db.execute("SELECT * FROM bin ORDER BY location").fetchall()
    return await render_template("kanbans/form.html", kanban=kanban, parts=parts, bins=bins)


@bp.route("/<int:id>", methods=["POST"])
@authorize
async def update(id):
    """Update a kanban."""
    db = get_db()
    form = await request.form
    
    part_id = form.get("part_id")
    bin_id = form.get("bin_id")
    kanban_quantity = form.get("kanban_quantity", "100")
    safety_lead_time_days = form.get("safety_lead_time_days", "0")
    estimated_daily_demand = form.get("estimated_daily_demand", "0")
    is_active = form.get("is_active") == "on"
    
    if not part_id or not bin_id:
        await flash("Part and Location are required.", "danger")
        return redirect(url_for("kanbans.edit", id=id))
    
    try:
        kanban_quantity = int(kanban_quantity) if kanban_quantity else 100
        safety_lead_time_days = float(safety_lead_time_days) if safety_lead_time_days else 0
        estimated_daily_demand = float(estimated_daily_demand) if estimated_daily_demand else 0
    except ValueError:
        await flash("Invalid quantity values.", "danger")
        return redirect(url_for("kanbans.edit", id=id))
    
    # Calculate number of cards: ceil((Demand × (Lead Time + Safety LT)) / Container Qty)
    part = db.execute("SELECT reorder_lead_time_days FROM part WHERE id = ?", [part_id]).fetchone()
    lead_time = part["reorder_lead_time_days"] if part else 7
    total_lt = lead_time + safety_lead_time_days
    if kanban_quantity > 0 and estimated_daily_demand > 0:
        number_of_cards = max(1, math.ceil((estimated_daily_demand * total_lt) / kanban_quantity))
    else:
        number_of_cards = 1
    
    db.execute(
        """UPDATE kanban SET part_id = ?, bin_id = ?, kanban_quantity = ?, 
           safety_lead_time_days = ?, estimated_daily_demand = ?,
           number_of_cards = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        [part_id, bin_id, kanban_quantity,
         safety_lead_time_days, estimated_daily_demand, number_of_cards, 1 if is_active else 0, id]
    )
    db.commit()
    
    await flash("Kanban updated successfully.", "success")
    return redirect(url_for("kanbans.detail", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
@authorize
async def delete(id):
    """Delete a kanban."""
    db = get_db()
    
    # Check if kanban has events
    event_count = db.execute(
        "SELECT COUNT(*) FROM kanban_event WHERE kanban_id = ?", [id]
    ).fetchone()[0]
    
    if event_count > 0:
        await flash(f"Cannot delete kanban: it has {event_count} event(s). Consider deactivating instead.", "danger")
        return redirect(url_for("kanbans.detail", id=id))
    
    db.execute("DELETE FROM kanban WHERE id = ?", [id])
    db.commit()
    await flash("Kanban deleted.", "success")
    
    return redirect(url_for("kanbans.list"))


@bp.route("/<int:id>/print")
@authorize
async def print_card(id):
    """Show printable kanban card."""
    db = get_db()
    kanban = db.execute(
        """
        SELECT
            k.*,
            p.part_number as part_name,
            p.manufacturer,
            p.description as part_description,
            p.reorder_lead_time_days,
            b.location as bin_location,
            u.abbreviation as uom_abbr,
            CAST(k.estimated_daily_demand * (p.reorder_lead_time_days + k.safety_lead_time_days) AS INTEGER) as reorder_point
        FROM kanban k
            JOIN part p ON k.part_id = p.id
            JOIN bin b ON k.bin_id = b.id
            JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
        WHERE k.id = ?
        """,
        [id]
    ).fetchone()
    
    if not kanban:
        await flash("Kanban not found.", "danger")
        return redirect(url_for("kanbans.list"))
    
    host = "127.0.0.1"
    printer = ZebraPrinter(host)
    
    for i in range(1, kanban["number_of_cards"] + 1):
        print((kanban, i))
    
    await flash("Kanban card(s) printed.", "success")
    
    return redirect(url_for("kanbans.detail", id=id))
