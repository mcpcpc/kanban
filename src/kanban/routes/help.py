from quart import Blueprint
from quart import render_template

from kanban.oauth import authorize

bp = Blueprint("help", __name__, url_prefix="/help")


@bp.route("/")
@authorize
async def index():
    """Help and documentation page."""
    return await render_template("help/index.html")
