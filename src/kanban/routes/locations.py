from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.deps import get_location_repo, get_kanban_repo

bp = Blueprint("locations", __name__, url_prefix="/locations")

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
async def index():
    """List all locations."""
    repo = get_location_repo()
    search = request.args.get("search", "").strip()
    color_filter = request.args.get("color", "").strip()

    locations = repo.find_all(search=search, color=color_filter)
    location_kanban_counts = repo.get_kanban_counts()
    colors_in_use = repo.get_colors_in_use()

    return await render_template(
        "locations/list.html", locations=locations,
        location_kanban_counts=location_kanban_counts,
        search=search, color_filter=color_filter,
        colors_in_use=colors_in_use, location_colors=LOCATION_COLORS,
    )


@bp.route("/new")
async def new():
    """Show new location form."""
    return await render_template("locations/form.html", location=None, location_colors=LOCATION_COLORS)


@bp.route("/", methods=["POST"])
async def create():
    """Create a new location."""
    form = await request.form
    location = form.get("location", "").strip()
    if not location:
        await flash("Location is required.", "danger")
        return redirect(url_for("locations.new"))

    try:
        get_location_repo().create(
            location=location,
            description=form.get("description", "").strip() or None,
            color=form.get("color", "").strip() or None,
        )
        await flash(f"Location '{location}' created successfully.", "success")
    except Exception as e:
        await flash(f"Error creating location: {str(e)}", "danger")
        return redirect(url_for("locations.new"))

    return redirect(url_for("locations.index"))


@bp.route("/<int:id>")
async def detail(id):
    """Show location details."""
    location = get_location_repo().find_by_id(id)
    if not location:
        await flash("Location not found.", "danger")
        return redirect(url_for("locations.index"))
    kanbans = get_kanban_repo().find_by_location_id(id)
    return await render_template(
        "locations/detail.html", location=location, kanbans=kanbans,
        location_colors=LOCATION_COLORS,
    )


@bp.route("/<int:id>/edit")
async def edit(id):
    """Show edit location form."""
    location = get_location_repo().find_by_id(id)
    if not location:
        await flash("Location not found.", "danger")
        return redirect(url_for("locations.index"))
    return await render_template("locations/form.html", location=location, location_colors=LOCATION_COLORS)


@bp.route("/<int:id>", methods=["POST"])
async def update(id):
    """Update a location."""
    form = await request.form
    location = form.get("location", "").strip()
    if not location:
        await flash("Location is required.", "danger")
        return redirect(url_for("locations.edit", id=id))

    get_location_repo().update(
        id, location=location,
        description=form.get("description", "").strip() or None,
        color=form.get("color", "").strip() or None,
    )
    await flash(f"Location '{location}' updated successfully.", "success")
    return redirect(url_for("locations.detail", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
async def delete(id):
    """Delete a location."""
    repo = get_location_repo()
    kanban_count = repo.count_kanbans(id)
    if kanban_count > 0:
        await flash(f"Cannot delete location: it is used in {kanban_count} kanban(s).", "danger")
        return redirect(url_for("locations.detail", id=id))

    location = repo.find_by_id(id)
    if location:
        repo.delete(id)
        await flash(f"Location '{location['location']}' deleted.", "success")
    return redirect(url_for("locations.index"))
