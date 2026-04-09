import csv
from io import StringIO

from quart import Blueprint, render_template, request, Response

from kanban.deps import get_event_repo

bp = Blueprint("events", __name__, url_prefix="/events")


@bp.route("/")
async def history():
    """Show event history with filters."""
    repo = get_event_repo()
    search = request.args.get("search", "").strip()
    event_type = request.args.get("type", "").strip()
    kanban_id = request.args.get("kanban_id", "").strip()

    events = repo.find_all_with_details(
        search=search, event_type=event_type, kanban_id=kanban_id,
    )
    event_types = repo.get_all_event_types()

    return await render_template(
        "events/history.html", events=events, event_types=event_types,
        search=search, selected_type=event_type, kanban_id=kanban_id,
    )


@bp.route("/export")
async def export():
    """Export events as CSV."""
    event_type = request.args.get("type", "").strip()
    kanban_id = request.args.get("kanban_id", "").strip()

    events = get_event_repo().find_all_with_details(
        event_type=event_type, kanban_id=kanban_id, limit=10_000,
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Event Type", "Quantity", "Notes",
                     "Kanban ID", "Part Number", "Manufacturer", "Bin Location"])

    for event in events:
        writer.writerow([
            event["id"],
            event["created_at"].isoformat() if event["created_at"] else "",
            event["event_type"],
            event["quantity"] or "",
            event["notes"] or "",
            event["kanban_id"],
            event["part_name"],
            event["manufacturer"],
            event["location_name"],
        ])

    return Response(
        output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=events.csv"},
    )
