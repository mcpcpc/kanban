from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.auth import manager_required
from kanban.deps import get_location_service

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
    search = request.args.get("search", "").strip()
    color_filter = request.args.get("color", "").strip()
    locations, location_kanban_counts, colors_in_use = get_location_service().list(
        search=search, color=color_filter,
    )
    return await render_template(
        "locations/list.html", locations=locations,
        location_kanban_counts=location_kanban_counts,
        search=search, color_filter=color_filter,
        colors_in_use=colors_in_use, location_colors=LOCATION_COLORS,
    )


@bp.route("/new")
@manager_required
async def new():
    return await render_template("locations/form.html", location=None, location_colors=LOCATION_COLORS)


@bp.route("/", methods=["POST"])
@manager_required
async def create():
    form = await request.form
    location = form.get("location", "").strip()
    if not location:
        await flash("Location is required.", "danger")
        return redirect(url_for("locations.new"))
    result = get_location_service().create(
        location=location,
        description=form.get("description", "").strip() or None,
        color=form.get("color", "").strip() or None,
    )
    await flash(result.message, result.category)
    return redirect(url_for("locations.index") if result.success else url_for("locations.new"))


@bp.route("/<int:id>")
async def detail(id):
    location, kanbans = get_location_service().get_detail(id)
    if not location:
        await flash("Location not found.", "danger")
        return redirect(url_for("locations.index"))
    return await render_template(
        "locations/detail.html", location=location, kanbans=kanbans,
        location_colors=LOCATION_COLORS,
    )


@bp.route("/<int:id>/edit")
@manager_required
async def edit(id):
    location = get_location_service().get_edit_context(id)
    if not location:
        await flash("Location not found.", "danger")
        return redirect(url_for("locations.index"))
    return await render_template("locations/form.html", location=location, location_colors=LOCATION_COLORS)


@bp.route("/<int:id>", methods=["POST"])
@manager_required
async def update(id):
    form = await request.form
    location = form.get("location", "").strip()
    if not location:
        await flash("Location is required.", "danger")
        return redirect(url_for("locations.edit", id=id))
    result = get_location_service().update(
        id, location=location,
        description=form.get("description", "").strip() or None,
        color=form.get("color", "").strip() or None,
    )
    await flash(result.message, result.category)
    return redirect(url_for("locations.detail", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
@manager_required
async def delete(id):
    result = get_location_service().delete(id)
    await flash(result.message, result.category)
    return redirect(url_for("locations.index") if result.success else url_for("locations.detail", id=id))
