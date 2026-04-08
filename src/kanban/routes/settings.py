from quart import Blueprint, current_app, render_template, request, redirect, url_for, flash

from kanban.db import get_db
from kanban.datawedge import is_datawedge_running
from kanban.datawedge import start_datawedge_server
from kanban.datawedge import stop_datawedge_server

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/")
async def index():
    """Show settings page."""
    db = get_db()
    setting = db.execute("SELECT * FROM setting LIMIT 1").fetchone()
    datawedge_status = "Running" if is_datawedge_running() else "Stopped"
    return await render_template(
        "settings/index.html",
        setting=setting,
        datawedge_status=datawedge_status
    )


@bp.route("/save", methods=["POST"])
async def save():
    """Save application settings."""
    form = await request.form
    printer_hostname = form.get("printer_hostname", "").strip()
    printer_port = int(form.get("printer_port", 9100))
    printer_timeout_seconds = float(form.get("printer_timeout_seconds", 10.0))
    label_template = form.get("label_template", "").strip()

    db = get_db()
    db.execute(
        "UPDATE setting SET printer_hostname = ?, printer_port = ?, "
        "printer_timeout_seconds = ?, label_template = ?, "
        "updated_at = CURRENT_TIMESTAMP "
        "WHERE id = 1",
        (printer_hostname, printer_port, printer_timeout_seconds, label_template),
    )
    db.commit()
    await flash("Settings saved successfully.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/datawedge/start")
async def start_datawedge():
    """Start the DataWedge server."""
    app = current_app._get_current_object()
    if await start_datawedge_server(app, "0.0.0.0", 58627):
        await flash("DataWedge server started successfully.", "success")
    else:
        await flash("Failed to start DataWedge server. Check logs for details.", "danger")

    return redirect(url_for("settings.index"))


@bp.route("/datawedge/stop")
async def stop_datawedge():
    """Stop the DataWedge server."""
    app = current_app._get_current_object()
    if await stop_datawedge_server(app):
        await flash("DataWedge server stopped successfully.", "success")
    else:
        await flash("Failed to stop DataWedge server. Check logs for details.", "danger")

    return redirect(url_for("settings.index"))
