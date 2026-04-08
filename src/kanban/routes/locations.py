from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.db import get_db

bp = Blueprint("locations", __name__, url_prefix="/locations")

# Available colors for location tagging
LOCATION_COLORS = [
    ("red", "#ef4444", "#fef2f2"),
    ("orange", "#f97316", "#fff7ed"),
    ("yellow", "#eab308", "#fefce8"),
    ("green", "#22c55e", "#f0fdf4"),
    ("blue", "#3b82f6", "#eff6ff"),
    ("purple", "#a855f7", "#faf5ff"),
    ("pink", "#ec4899", "#fdf2f8"),
    ("gray", "#6b7280", "#f9fafb"),
]


@bp.route("/")
async def list():
    """List all locations."""
    db = get_db()
    
    search = request.args.get("search", "").strip()
    color_filter = request.args.get("color", "").strip()
    
    query = "SELECT * FROM location WHERE 1=1"
    params = []
    
    if search:
        query += " AND (location LIKE ? OR description LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param])
    
    if color_filter:
        query += " AND color = ?"
        params.append(color_filter)
    
    query += " ORDER BY location"
    
    locations = db.execute(query, params).fetchall()
    
    # Get kanban counts for each location
    location_kanban_counts = {}
    for location in locations:
        count = db.execute(
            "SELECT COUNT(*) FROM kanban WHERE location_id = ? AND is_active = 1",
            [location["id"]]
        ).fetchone()[0]
        location_kanban_counts[location["id"]] = count
    
    # Get distinct colors in use for filter dropdown
    colors_in_use = db.execute(
        "SELECT DISTINCT color FROM location WHERE color IS NOT NULL ORDER BY color"
    ).fetchall()
    colors_in_use = [row["color"] for row in colors_in_use]
    
    return await render_template(
        "locations/list.html",
        locations=locations,
        location_kanban_counts=location_kanban_counts,
        search=search,
        color_filter=color_filter,
        colors_in_use=colors_in_use,
        location_colors=LOCATION_COLORS
    )


@bp.route("/new")
async def new():
    """Show new location form."""
    return await render_template("locations/form.html", location=None, location_colors=LOCATION_COLORS)


@bp.route("/", methods=["POST"])
async def create():
    """Create a new location."""
    db = get_db()
    form = await request.form
    
    location = form.get("location", "").strip()
    description = form.get("description", "").strip()
    color = form.get("color", "").strip() or None
    
    if not location:
        await flash("Location is required.", "danger")
        return redirect(url_for("locations.new"))
    
    try:
        db.execute(
            "INSERT INTO location (location, description, color) VALUES (?, ?, ?)",
            [location, description or None, color]
        )
        db.commit()
        await flash(f"Location '{location}' created successfully.", "success")
    except Exception as e:
        await flash(f"Error creating location: {str(e)}", "danger")
        return redirect(url_for("locations.new"))
    
    return redirect(url_for("locations.list"))


@bp.route("/<int:id>")
async def detail(id):
    """Show location details."""
    db = get_db()
    location = db.execute("SELECT * FROM location WHERE id = ?", [id]).fetchone()
    
    if not location:
        await flash("Location not found.", "danger")
        return redirect(url_for("locations.list"))
    
    # Get kanbans in this location
    kanbans = db.execute(
        """SELECT k.*, p.part_number as part_name, p.manufacturer
           FROM kanban k
           JOIN part p ON k.part_id = p.id
           WHERE k.location_id = ?
           ORDER BY p.part_number""",
        [id]
    ).fetchall()
    
    return await render_template("locations/detail.html", location=location, kanbans=kanbans, location_colors=LOCATION_COLORS)


@bp.route("/<int:id>/edit")
async def edit(id):
    """Show edit location form."""
    db = get_db()
    location = db.execute("SELECT * FROM location WHERE id = ?", [id]).fetchone()
    
    if not location:
        await flash("Location not found.", "danger")
        return redirect(url_for("locations.list"))
    
    return await render_template("locations/form.html", location=location, location_colors=LOCATION_COLORS)


@bp.route("/<int:id>", methods=["POST"])
async def update(id):
    """Update a location."""
    db = get_db()
    form = await request.form
    
    location = form.get("location", "").strip()
    description = form.get("description", "").strip()
    color = form.get("color", "").strip() or None
    
    if not location:
        await flash("Location is required.", "danger")
        return redirect(url_for("locations.edit", id=id))
    
    db.execute(
        """UPDATE location SET location = ?, description = ?, color = ?,
           updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
        [location, description or None, color, id]
    )
    db.commit()
    await flash(f"Location '{location}' updated successfully.", "success")
    
    return redirect(url_for("locations.detail", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
async def delete(id):
    """Delete a location."""
    db = get_db()
    
    # Check if location is used in any kanbans
    kanban_count = db.execute(
        "SELECT COUNT(*) FROM kanban WHERE location_id = ?", [id]
    ).fetchone()[0]
    
    if kanban_count > 0:
        await flash(f"Cannot delete location: it is used in {kanban_count} kanban(s).", "danger")
        return redirect(url_for("locations.detail", id=id))
    
    location = db.execute("SELECT location FROM location WHERE id = ?", [id]).fetchone()
    if location:
        db.execute("DELETE FROM location WHERE id = ?", [id])
        db.commit()
        await flash(f"Location '{location['location']}' deleted.", "success")
    
    return redirect(url_for("locations.list"))
