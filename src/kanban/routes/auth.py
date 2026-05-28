from quart import Blueprint, g, render_template, request, redirect, url_for, flash, session

from kanban.deps import get_user_service

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
            import time
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
