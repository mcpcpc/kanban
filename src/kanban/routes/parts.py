from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.db import get_db

bp = Blueprint("parts", __name__, url_prefix="/parts")

ITEMS_PER_PAGE = 20


@bp.route("/")
async def list():
    """List all parts with search and filter."""
    db = get_db()
    
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    page = request.args.get("page", 1, type=int)
    page = max(1, page)
    
    query = """
        SELECT p.*, u.name as uom_name, u.abbreviation as uom_abbr
        FROM part p
        JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
        WHERE 1=1
    """
    params = []
    
    if search:
        query += " AND (p.part_number LIKE ? OR p.manufacturer LIKE ? OR p.description LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
    
    if category:
        query += " AND p.category = ?"
        params.append(category)
    
    # Get total count for pagination
    count_query = query.replace(
        "SELECT p.*, u.name as uom_name, u.abbreviation as uom_abbr",
        "SELECT COUNT(*)"
    )
    total_count = db.execute(count_query, params).fetchone()[0]
    total_pages = (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    query += " ORDER BY p.part_number LIMIT ? OFFSET ?"
    params.extend([ITEMS_PER_PAGE, (page - 1) * ITEMS_PER_PAGE])
    
    parts = db.execute(query, params).fetchall()
    
    # Get distinct categories for filter dropdown
    categories = db.execute(
        "SELECT DISTINCT category FROM part WHERE category IS NOT NULL AND category != '' ORDER BY category"
    ).fetchall()
    
    return await render_template(
        "parts/list.html",
        parts=parts,
        categories=categories,
        search=search,
        selected_category=category,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )


@bp.route("/new")
async def new():
    """Show new part form."""
    db = get_db()
    units = db.execute("SELECT * FROM unit_of_measure").fetchall()
    return await render_template("parts/form.html", part=None, units=units)


@bp.route("/", methods=["POST"])
async def create():
    """Create a new part."""
    db = get_db()
    form = await request.form
    
    part_number = form.get("part_number", "").strip()
    manufacturer = form.get("manufacturer", "").strip()
    description = form.get("description", "").strip()
    category = form.get("category", "").strip()
    datasheet = form.get("datasheet", "").strip()
    unit_of_measure_id = form.get("unit_of_measure_id")
    reorder_lead_time_days = form.get("reorder_lead_time_days", "7")
    
    if not part_number:
        await flash("Part number is required.", "danger")
        return redirect(url_for("parts.new"))
    
    if not manufacturer:
        await flash("Manufacturer is required.", "danger")
        return redirect(url_for("parts.new"))
    
    try:
        reorder_lead_time_days = float(reorder_lead_time_days) if reorder_lead_time_days else 7.0
    except ValueError:
        reorder_lead_time_days = 7.0
    
    try:
        db.execute(
            """INSERT INTO part (part_number, manufacturer, description, category, datasheet, 
               unit_of_measure_id, reorder_lead_time_days)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [part_number, manufacturer, description or None, category or None, 
             datasheet or None, unit_of_measure_id, reorder_lead_time_days]
        )
        db.commit()
        await flash(f"Part '{part_number}' created successfully.", "success")
    except db.IntegrityError:
        await flash(f"A part with number '{part_number}' already exists.", "danger")
        return redirect(url_for("parts.new"))
    
    return redirect(url_for("parts.list"))


@bp.route("/<int:id>")
async def detail(id):
    """Show part details."""
    db = get_db()
    part = db.execute(
        """SELECT p.*, u.name as uom_name, u.abbreviation as uom_abbr
           FROM part p
           JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
           WHERE p.id = ?""",
        [id]
    ).fetchone()
    
    if not part:
        await flash("Part not found.", "danger")
        return redirect(url_for("parts.list"))
    
    # Get kanbans using this part
    kanbans = db.execute(
        """SELECT k.*, b.location as bin_location
           FROM kanban k
           JOIN bin b ON k.bin_id = b.id
           WHERE k.part_id = ?
           ORDER BY b.location""",
        [id]
    ).fetchall()
    
    return await render_template("parts/detail.html", part=part, kanbans=kanbans)


@bp.route("/<int:id>/edit")
async def edit(id):
    """Show edit part form."""
    db = get_db()
    part = db.execute("SELECT * FROM part WHERE id = ?", [id]).fetchone()
    
    if not part:
        await flash("Part not found.", "danger")
        return redirect(url_for("parts.list"))
    
    units = db.execute("SELECT * FROM unit_of_measure ORDER BY name").fetchall()
    return await render_template("parts/form.html", part=part, units=units)


@bp.route("/<int:id>", methods=["POST"])
async def update(id):
    """Update a part."""
    db = get_db()
    form = await request.form
    
    part_number = form.get("part_number", "").strip()
    manufacturer = form.get("manufacturer", "").strip()
    description = form.get("description", "").strip()
    category = form.get("category", "").strip()
    datasheet = form.get("datasheet", "").strip()
    unit_of_measure_id = form.get("unit_of_measure_id")
    reorder_lead_time_days = form.get("reorder_lead_time_days", "7")
    
    if not part_number:
        await flash("Part number is required.", "danger")
        return redirect(url_for("parts.edit", id=id))
    
    if not manufacturer:
        await flash("Manufacturer is required.", "danger")
        return redirect(url_for("parts.edit", id=id))
    
    try:
        reorder_lead_time_days = float(reorder_lead_time_days) if reorder_lead_time_days else 7.0
    except ValueError:
        reorder_lead_time_days = 7.0
    
    try:
        db.execute(
            """UPDATE part SET part_number = ?, manufacturer = ?, description = ?, 
               category = ?, datasheet = ?, unit_of_measure_id = ?,
               reorder_lead_time_days = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [part_number, manufacturer, description or None, category or None,
             datasheet or None, unit_of_measure_id, reorder_lead_time_days, id]
        )
        db.commit()
        await flash(f"Part '{part_number}' updated successfully.", "success")
    except db.IntegrityError:
        await flash(f"A part with number '{part_number}' already exists.", "danger")
        return redirect(url_for("parts.edit", id=id))
    
    return redirect(url_for("parts.detail", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
async def delete(id):
    """Delete a part."""
    db = get_db()
    
    # Check if part is used in any kanbans
    kanban_count = db.execute(
        "SELECT COUNT(*) FROM kanban WHERE part_id = ?", [id]
    ).fetchone()[0]
    
    if kanban_count > 0:
        await flash(f"Cannot delete part: it is used in {kanban_count} kanban(s).", "danger")
        return redirect(url_for("parts.detail", id=id))
    
    part = db.execute("SELECT part_number FROM part WHERE id = ?", [id]).fetchone()
    if part:
        db.execute("DELETE FROM part WHERE id = ?", [id])
        db.commit()
        await flash(f"Part '{part['part_number']}' deleted.", "success")
    
    return redirect(url_for("parts.list"))
