from sqlite3 import IntegrityError

from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.deps import get_part_repo, get_kanban_repo

bp = Blueprint("parts", __name__, url_prefix="/parts")

ITEMS_PER_PAGE = 20


@bp.route("/")
async def index():
    """List all parts with search and filter."""
    repo = get_part_repo()
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    page = max(1, request.args.get("page", 1, type=int))

    parts, total_count = repo.find_all(
        search=search, category=category, page=page, per_page=ITEMS_PER_PAGE,
    )
    total_pages = (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    categories = repo.get_categories()

    return await render_template(
        "parts/list.html", parts=parts, categories=categories,
        search=search, selected_category=category,
        page=page, total_pages=total_pages, total_count=total_count,
    )


@bp.route("/new")
async def new():
    """Show new part form."""
    units = get_part_repo().get_units_of_measure()
    return await render_template("parts/form.html", part=None, units=units)


@bp.route("/", methods=["POST"])
async def create():
    """Create a new part."""
    form = await request.form
    part_number = form.get("part_number", "").strip()
    manufacturer = form.get("manufacturer", "").strip()

    if not part_number:
        await flash("Part number is required.", "danger")
        return redirect(url_for("parts.new"))
    if not manufacturer:
        await flash("Manufacturer is required.", "danger")
        return redirect(url_for("parts.new"))

    try:
        rlt = float(form.get("reorder_lead_time_days", "7") or "7")
    except ValueError:
        rlt = 7.0

    try:
        get_part_repo().create(
            part_number=part_number, manufacturer=manufacturer,
            description=form.get("description", "").strip() or None,
            category=form.get("category", "").strip() or None,
            datasheet=form.get("datasheet", "").strip() or None,
            unit_of_measure_id=form.get("unit_of_measure_id"),
            reorder_lead_time_days=rlt,
        )
        await flash(f"Part '{part_number}' created successfully.", "success")
    except IntegrityError:
        await flash(f"A part with number '{part_number}' already exists.", "danger")
        return redirect(url_for("parts.new"))

    return redirect(url_for("parts.index"))


@bp.route("/<int:id>")
async def detail(id):
    """Show part details."""
    part = get_part_repo().find_with_uom(id)
    if not part:
        await flash("Part not found.", "danger")
        return redirect(url_for("parts.index"))
    kanbans = get_kanban_repo().find_by_part_id(id)
    return await render_template("parts/detail.html", part=part, kanbans=kanbans)


@bp.route("/<int:id>/edit")
async def edit(id):
    """Show edit part form."""
    repo = get_part_repo()
    part = repo.find_by_id(id)
    if not part:
        await flash("Part not found.", "danger")
        return redirect(url_for("parts.index"))
    units = repo.get_units_of_measure()
    return await render_template("parts/form.html", part=part, units=units)


@bp.route("/<int:id>", methods=["POST"])
async def update(id):
    """Update a part."""
    form = await request.form
    part_number = form.get("part_number", "").strip()
    manufacturer = form.get("manufacturer", "").strip()

    if not part_number:
        await flash("Part number is required.", "danger")
        return redirect(url_for("parts.edit", id=id))
    if not manufacturer:
        await flash("Manufacturer is required.", "danger")
        return redirect(url_for("parts.edit", id=id))

    try:
        rlt = float(form.get("reorder_lead_time_days", "7") or "7")
    except ValueError:
        rlt = 7.0

    try:
        get_part_repo().update(
            id, part_number=part_number, manufacturer=manufacturer,
            description=form.get("description", "").strip() or None,
            category=form.get("category", "").strip() or None,
            datasheet=form.get("datasheet", "").strip() or None,
            unit_of_measure_id=form.get("unit_of_measure_id"),
            reorder_lead_time_days=rlt,
        )
        await flash(f"Part '{part_number}' updated successfully.", "success")
    except IntegrityError:
        await flash(f"A part with number '{part_number}' already exists.", "danger")
        return redirect(url_for("parts.edit", id=id))

    return redirect(url_for("parts.detail", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
async def delete(id):
    """Delete a part."""
    repo = get_part_repo()
    kanban_count = repo.count_kanbans(id)
    if kanban_count > 0:
        await flash(f"Cannot delete part: it is used in {kanban_count} kanban(s).", "danger")
        return redirect(url_for("parts.detail", id=id))

    part = repo.find_by_id(id)
    if part:
        repo.delete(id)
        await flash(f"Part '{part['part_number']}' deleted.", "success")
    return redirect(url_for("parts.index"))
