from quart import Blueprint, g, render_template, request, redirect, url_for, flash

from kanban.auth import admin_required
from kanban.deps import get_user_service
from kanban.services.user import UserService

bp = Blueprint("users", __name__, url_prefix="/users")


@bp.route("/")
@admin_required
async def index():
    users = get_user_service().list()
    return await render_template("users/list.html", users=users)


@bp.route("/new")
@admin_required
async def new():
    return await render_template(
        "users/form.html", user=None, roles=UserService.ROLES,
    )


@bp.route("/", methods=["POST"])
@admin_required
async def create():
    form = await request.form
    result = get_user_service().create(
        email=form.get("email", "").strip(),
        display_name=form.get("display_name", "").strip(),
        password=form.get("password", ""),
        role=form.get("role", "user"),
    )
    await flash(result.message, result.category)
    return redirect(url_for("users.index") if result.success else url_for("users.new"))


@bp.route("/<int:id>/edit")
@admin_required
async def edit(id):
    user = get_user_service().get_by_id(id)
    if not user:
        await flash("User not found.", "danger")
        return redirect(url_for("users.index"))
    return await render_template(
        "users/form.html", user=user, roles=UserService.ROLES,
    )


@bp.route("/<int:id>", methods=["POST"])
@admin_required
async def update(id):
    form = await request.form
    result = get_user_service().update(
        id,
        email=form.get("email", "").strip(),
        display_name=form.get("display_name", "").strip(),
        role=form.get("role", "user"),
        is_active=form.get("is_active") == "on",
        current_user_id=g.current_user["id"],
    )
    await flash(result.message, result.category)
    return redirect(url_for("users.index") if result.success else url_for("users.edit", id=id))


@bp.route("/<int:id>/password", methods=["POST"])
@admin_required
async def set_password(id):
    form = await request.form
    result = get_user_service().set_password(id, form.get("password", ""))
    await flash(result.message, result.category)
    return redirect(url_for("users.edit", id=id))
