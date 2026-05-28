from quart import Blueprint, render_template, request, redirect, url_for, flash, make_response

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
    email = form.get("email", "").strip()
    display_name = form.get("display_name", "").strip()
    result = get_user_service().create(
        email=email,
        display_name=display_name,
        role=form.get("role", "user"),
    )
    if not result.success:
        await flash(result.message, result.category)
        return redirect(url_for("users.new"))
    reset_url = url_for("auth.reset_password", token=result.data["token"], _external=True)
    response = await make_response(
        await render_template(
            "users/created.html",
            display_name=display_name,
            email=email,
            reset_url=reset_url,
        )
    )
    response.headers["Cache-Control"] = "no-store"
    return response


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


@bp.route("/<int:id>/reset-link", methods=["POST"])
@admin_required
async def generate_reset_link(id):
    result = get_user_service().generate_reset_link(id)
    if not result.success:
        await flash(result.message, result.category)
        return redirect(url_for("users.edit", id=id))
    reset_url = url_for("auth.reset_password", token=result.data["token"], _external=True)
    user = get_user_service().get_by_id(id)
    response = await make_response(
        await render_template(
            "users/created.html",
            display_name=user["display_name"],
            email=user["email"],
            reset_url=reset_url,
        )
    )
    response.headers["Cache-Control"] = "no-store"
    return response
