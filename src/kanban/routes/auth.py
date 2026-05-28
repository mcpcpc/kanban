import time

from quart import Blueprint, g, render_template, request, redirect, url_for, flash, session

from kanban.deps import get_user_service, get_user_repo

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
async def login():
    if g.current_user:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        form = await request.form
        email = form.get("email", "").strip()
        password = form.get("password", "")

        user = get_user_service().authenticate(email, password)
        if user:
            session.permanent = True
            session["user_id"] = user["id"]
            session["_last_active"] = time.time()
            next_url = request.args.get("next") or url_for("dashboard.index")
            return redirect(next_url)

        await flash("Invalid email or password.", "danger")

    return await render_template("auth/login.html")


@bp.route("/logout")
async def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
async def reset_password(token):
    user = get_user_repo().find_by_reset_token(token)
    if not user:
        await flash("This setup link is invalid or has already been used.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        form = await request.form
        result = get_user_service().activate_with_token(token, form.get("password", ""))
        if result.success:
            session.permanent = True
            session["user_id"] = result.data["user_id"]
            session["_last_active"] = time.time()
            await flash(result.message, "success")
            return redirect(url_for("dashboard.index"))
        await flash(result.message, result.category)

    return await render_template("auth/reset_password.html", token=token, user=user)
