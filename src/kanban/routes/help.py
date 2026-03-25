from quart import Blueprint
from quart import render_template

bp = Blueprint("help", __name__, url_prefix="/help")


@bp.route("/")
async def index():
    """Help and documentation page."""
    return await render_template("help/index.html")
