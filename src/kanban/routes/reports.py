from quart import Blueprint, render_template

from kanban.deps import get_report_service

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
async def index():
    """Reports dashboard."""
    data = get_report_service().get_report()
    return await render_template("reports/index.html", **data)
