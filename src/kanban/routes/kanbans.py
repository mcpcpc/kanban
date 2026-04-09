from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.deps import get_kanban_service, get_print_service

bp = Blueprint("kanbans", __name__, url_prefix="/kanbans")


@bp.route("/")
async def index():
    """List all kanbans."""
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    kanbans = get_kanban_service().list(search, status)
    return await render_template(
        "kanbans/list.html", kanbans=kanbans, search=search, selected_status=status,
    )


@bp.route("/new")
async def new():
    """Show new kanban form."""
    parts, locations = get_kanban_service().get_new_context()
    selected_location_id = request.args.get("location_id", type=int)
    selected_part_id = request.args.get("part_id", type=int)
    return await render_template(
        "kanbans/form.html", kanban=None, parts=parts, locations=locations,
        selected_location_id=selected_location_id, selected_part_id=selected_part_id,
    )


@bp.route("/", methods=["POST"])
async def create():
    """Create a new kanban."""
    form = await request.form
    result = get_kanban_service().create(
        part_id=form.get("part_id"),
        location_id=form.get("location_id"),
        kanban_quantity=form.get("kanban_quantity", "100"),
        safety_lead_time_days=form.get("safety_lead_time_days", "0"),
        estimated_daily_demand=form.get("estimated_daily_demand", "0"),
        is_active=form.get("is_active") == "on",
    )
    await flash(result.message, result.category)
    if result.success:
        return redirect(url_for("kanbans.detail", id=result.data["id"]))
    return redirect(url_for("kanbans.new"))


@bp.route("/<int:id>")
async def detail(id):
    """Show kanban details."""
    svc = get_kanban_service()
    kanban, events = svc.get_detail(id)
    if not kanban:
        await flash("Kanban not found.", "danger")
        return redirect(url_for("kanbans.index"))
    return await render_template("kanbans/detail.html", kanban=kanban, events=events)


@bp.route("/<int:id>/edit")
async def edit(id):
    """Show edit kanban form."""
    kanban, parts, locations = get_kanban_service().get_edit_context(id)
    if not kanban:
        await flash("Kanban not found.", "danger")
        return redirect(url_for("kanbans.index"))
    return await render_template("kanbans/form.html", kanban=kanban, parts=parts, locations=locations)


@bp.route("/<int:id>", methods=["POST"])
async def update(id):
    """Update a kanban."""
    form = await request.form
    result = get_kanban_service().update(
        id,
        part_id=form.get("part_id"),
        location_id=form.get("location_id"),
        kanban_quantity=form.get("kanban_quantity", "100"),
        safety_lead_time_days=form.get("safety_lead_time_days", "0"),
        estimated_daily_demand=form.get("estimated_daily_demand", "0"),
        is_active=form.get("is_active") == "on",
    )
    await flash(result.message, result.category)
    if result.success:
        return redirect(url_for("kanbans.detail", id=id))
    return redirect(url_for("kanbans.edit", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
async def delete(id):
    """Delete a kanban."""
    result = get_kanban_service().delete(id)
    await flash(result.message, result.category)
    if result.success:
        return redirect(url_for("kanbans.index"))
    return redirect(url_for("kanbans.detail", id=id))


@bp.route("/<int:id>/print")
async def print_card(id):
    """Print kanban card(s) to Zebra printer."""
    result = get_print_service().print_cards(id)
    await flash(result.message, result.category)
    return redirect(url_for("kanbans.detail", id=id))
