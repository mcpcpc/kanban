from quart import Blueprint, jsonify, request

from kanban.deps import get_kanban_service, get_report_service

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/kanbans")
async def list_kanbans():
    """List kanbans with status."""
    return jsonify(get_kanban_service().list_api())


@bp.route("/kanbans/<int:id>")
async def get_kanban(id):
    """Get kanban detail with recent events."""
    data = get_kanban_service().get_api_detail(id)
    if not data:
        return jsonify({"error": "Kanban not found"}), 404
    return jsonify(data)


@bp.route("/events", methods=["POST"])
async def record_event():
    """Record a kanban event."""
    data = await request.get_json()
    result = get_kanban_service().record_event_api(data)
    if not result.success:
        code = 409 if "already exists" in result.message else (404 if "not found" in result.message.lower() else 400)
        return jsonify({"error": result.message}), code
    return jsonify(result.data), 201


@bp.route("/health")
async def health():
    """System health summary."""
    return jsonify(get_report_service().get_health())


@bp.route("/metrics")
async def metrics():
    """Performance metrics."""
    return jsonify(get_report_service().get_metrics())


@bp.route("/kanbans/<int:id>/suggest-reorder-point")
async def suggest_reorder_point(id):
    """Calculate reorder point based on estimated demand, lead time, and safety stock."""
    data = get_kanban_service().suggest_reorder_point(id)
    if not data:
        return jsonify({"error": "Kanban not found"}), 404
    return jsonify(data)
