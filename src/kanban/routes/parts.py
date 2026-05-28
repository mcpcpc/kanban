from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.auth import manager_required
from kanban.deps import get_part_service

bp = Blueprint("parts", __name__, url_prefix="/parts")

ITEMS_PER_PAGE = 20


def _lead_time(form):
    try:
        return float(form.get("reorder_lead_time_days", "7") or "7")
    except ValueError:
        return 7.0


def _optional_fields(form):
    return dict(
        description=form.get("description", "").strip() or None,
        category=form.get("category", "").strip() or None,
        datasheet=form.get("datasheet", "").strip() or None,
        unit_of_measure_id=form.get("unit_of_measure_id"),
        reorder_lead_time_days=_lead_time(form),
    )


@bp.route("/")
async def index():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    parts, total_count, total_pages, categories = get_part_service().list(
        search=search, category=category, page=page, per_page=ITEMS_PER_PAGE,
    )
    return await render_template(
        "parts/list.html", parts=parts, categories=categories,
        search=search, selected_category=category,
        page=page, total_pages=total_pages, total_count=total_count,
    )


@bp.route("/new")
@manager_required
async def new():
    units = get_part_service().get_units_of_measure()
    return await render_template("parts/form.html", part=None, units=units)


@bp.route("/", methods=["POST"])
@manager_required
async def create():
    form = await request.form
    part_number = form.get("part_number", "").strip()
    manufacturer = form.get("manufacturer", "").strip()
    if not part_number:
        await flash("Part number is required.", "danger")
        return redirect(url_for("parts.new"))
    if not manufacturer:
        await flash("Manufacturer is required.", "danger")
        return redirect(url_for("parts.new"))
    result = get_part_service().create(
        part_number=part_number, manufacturer=manufacturer, **_optional_fields(form),
    )
    await flash(result.message, result.category)
    return redirect(url_for("parts.index") if result.success else url_for("parts.new"))


@bp.route("/<int:id>")
async def detail(id):
    part, kanbans = get_part_service().get_detail(id)
    if not part:
        await flash("Part not found.", "danger")
        return redirect(url_for("parts.index"))
    return await render_template("parts/detail.html", part=part, kanbans=kanbans)


@bp.route("/<int:id>/edit")
@manager_required
async def edit(id):
    part, units = get_part_service().get_edit_context(id)
    if not part:
        await flash("Part not found.", "danger")
        return redirect(url_for("parts.index"))
    return await render_template("parts/form.html", part=part, units=units)


@bp.route("/<int:id>", methods=["POST"])
@manager_required
async def update(id):
    form = await request.form
    part_number = form.get("part_number", "").strip()
    manufacturer = form.get("manufacturer", "").strip()
    if not part_number:
        await flash("Part number is required.", "danger")
        return redirect(url_for("parts.edit", id=id))
    if not manufacturer:
        await flash("Manufacturer is required.", "danger")
        return redirect(url_for("parts.edit", id=id))
    result = get_part_service().update(
        id, part_number=part_number, manufacturer=manufacturer, **_optional_fields(form),
    )
    await flash(result.message, result.category)
    return redirect(url_for("parts.detail", id=id) if result.success else url_for("parts.edit", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
@manager_required
async def delete(id):
    result = get_part_service().delete(id)
    await flash(result.message, result.category)
    return redirect(url_for("parts.index") if result.success else url_for("parts.detail", id=id))
