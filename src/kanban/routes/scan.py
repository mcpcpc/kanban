from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.deps import get_scan_service

bp = Blueprint("scan", __name__, url_prefix="/scan")


@bp.route("/")
async def index():
    """Quick scan interface."""
    return await render_template("scan/quick.html")


@bp.route("/", methods=["POST"])
async def process():
    """Process a scanned barcode."""
    form = await request.form
    result = get_scan_service().process_scan(
        barcode=form.get("barcode", "").strip(),
        action=form.get("action", "signal"),
        quantity=form.get("quantity", "").strip(),
        notes=form.get("notes", "").strip(),
    )
    await flash(result.message, result.category)
    return_to = form.get("return_to", "").strip()
    return redirect(return_to or url_for("scan.index"))
