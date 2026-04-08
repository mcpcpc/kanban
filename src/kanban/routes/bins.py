from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.db import get_db

bp = Blueprint("bins", __name__, url_prefix="/locations")

# Available colors for bin tagging
BIN_COLORS = [
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
    """List all bins."""
    db = get_db()
    
    search = request.args.get("search", "").strip()
    color_filter = request.args.get("color", "").strip()
    
    query = "SELECT * FROM bin WHERE 1=1"
    params = []
    
    if search:
        query += " AND (location LIKE ? OR description LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param])
    
    if color_filter:
        query += " AND color = ?"
        params.append(color_filter)
    
    query += " ORDER BY location"
    
    bins = db.execute(query, params).fetchall()
    
    # Get kanban counts for each bin
    bin_kanban_counts = {}
    for bin in bins:
        count = db.execute(
            "SELECT COUNT(*) FROM kanban WHERE bin_id = ? AND is_active = 1",
            [bin["id"]]
        ).fetchone()[0]
        bin_kanban_counts[bin["id"]] = count
    
    # Get distinct colors in use for filter dropdown
    colors_in_use = db.execute(
        "SELECT DISTINCT color FROM bin WHERE color IS NOT NULL ORDER BY color"
    ).fetchall()
    colors_in_use = [row["color"] for row in colors_in_use]
    
    return await render_template(
        "bins/list.html",
        bins=bins,
        bin_kanban_counts=bin_kanban_counts,
        search=search,
        color_filter=color_filter,
        colors_in_use=colors_in_use,
        bin_colors=BIN_COLORS
    )


@bp.route("/new")
async def new():
    """Show new bin form."""
    return await render_template("bins/form.html", bin=None, bin_colors=BIN_COLORS)


@bp.route("/", methods=["POST"])
async def create():
    """Create a new bin."""
    db = get_db()
    form = await request.form
    
    location = form.get("location", "").strip()
    description = form.get("description", "").strip()
    color = form.get("color", "").strip() or None
    
    if not location:
        await flash("Location is required.", "danger")
        return redirect(url_for("bins.new"))
    
    try:
        db.execute(
            "INSERT INTO bin (location, description, color) VALUES (?, ?, ?)",
            [location, description or None, color]
        )
        db.commit()
        await flash(f"Location '{location}' created successfully.", "success")
    except Exception as e:
        await flash(f"Error creating location: {str(e)}", "danger")
        return redirect(url_for("bins.new"))
    
    return redirect(url_for("bins.list"))


@bp.route("/<int:id>")
async def detail(id):
    """Show bin details."""
    db = get_db()
    bin = db.execute("SELECT * FROM bin WHERE id = ?", [id]).fetchone()
    
    if not bin:
        await flash("Location not found.", "danger")
        return redirect(url_for("bins.list"))
    
    # Get kanbans in this bin
    kanbans = db.execute(
        """SELECT k.*, p.part_number as part_name, p.manufacturer
           FROM kanban k
           JOIN part p ON k.part_id = p.id
           WHERE k.bin_id = ?
           ORDER BY p.part_number""",
        [id]
    ).fetchall()
    
    return await render_template("bins/detail.html", bin=bin, kanbans=kanbans, bin_colors=BIN_COLORS)


@bp.route("/<int:id>/edit")
async def edit(id):
    """Show edit bin form."""
    db = get_db()
    bin = db.execute("SELECT * FROM bin WHERE id = ?", [id]).fetchone()
    
    if not bin:
        await flash("Location not found.", "danger")
        return redirect(url_for("bins.list"))
    
    return await render_template("bins/form.html", bin=bin, bin_colors=BIN_COLORS)


@bp.route("/<int:id>", methods=["POST"])
async def update(id):
    """Update a bin."""
    db = get_db()
    form = await request.form
    
    location = form.get("location", "").strip()
    description = form.get("description", "").strip()
    color = form.get("color", "").strip() or None
    
    if not location:
        await flash("Location is required.", "danger")
        return redirect(url_for("bins.edit", id=id))
    
    db.execute(
        """UPDATE bin SET location = ?, description = ?, color = ?,
           updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
        [location, description or None, color, id]
    )
    db.commit()
    await flash(f"Location '{location}' updated successfully.", "success")
    
    return redirect(url_for("bins.detail", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
async def delete(id):
    """Delete a bin."""
    db = get_db()
    
    # Check if bin is used in any kanbans
    kanban_count = db.execute(
        "SELECT COUNT(*) FROM kanban WHERE bin_id = ?", [id]
    ).fetchone()[0]
    
    if kanban_count > 0:
        await flash(f"Cannot delete location: it is used in {kanban_count} kanban(s).", "danger")
        return redirect(url_for("bins.detail", id=id))
    
    bin = db.execute("SELECT location FROM bin WHERE id = ?", [id]).fetchone()
    if bin:
        db.execute("DELETE FROM bin WHERE id = ?", [id])
        db.commit()
        await flash(f"Location '{bin['location']}' deleted.", "success")
    
    return redirect(url_for("bins.list"))
