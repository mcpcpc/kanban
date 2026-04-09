from quart import Blueprint, render_template

from kanban.deps import get_dashboard_service

bp = Blueprint("dashboard", __name__)


@bp.route("/")
async def index():
    """Dashboard with system overview."""
    data = get_dashboard_service().get_overview()
    return await render_template("dashboard/index.html", **data)
