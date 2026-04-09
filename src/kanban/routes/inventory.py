import csv
from io import StringIO
from datetime import datetime

from quart import Blueprint, render_template, request, redirect, url_for, flash, Response

from kanban.deps import get_inventory_service, get_part_repo

bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@bp.route("/")
async def index():
    """Inventory list with stock levels and demand metrics."""
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    page = max(1, request.args.get("page", 1, type=int))

    svc = get_inventory_service()
    paginated_data, total_count, total_pages = svc.list(
        search=search, status_filter=status_filter, page=page,
    )

    return await render_template(
        "inventory/index.html",
        inventory_data=paginated_data,
        search=search,
        status_filter=status_filter,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
    )


@bp.route("/<int:part_id>/adjust", methods=["GET", "POST"])
async def adjust(part_id):
    """Adjust inventory quantity for a part."""
    part = get_part_repo().find_with_inventory(part_id)

    if not part:
        await flash("Part not found.", "danger")
        return redirect(url_for("inventory.index"))

    if request.method == "POST":
        form = await request.form
        try:
            quantity = float(form.get("quantity", "0"))
        except ValueError:
            await flash("Invalid quantity.", "danger")
            return redirect(url_for("inventory.adjust", part_id=part_id))

        result = get_inventory_service().adjust(
            part_id, part,
            adjustment_type=form.get("adjustment_type", "set"),
            quantity=quantity,
            reason=form.get("reason", "").strip(),
        )
        await flash(result.message, result.category)
        return redirect(url_for("inventory.index"))

    return await render_template("inventory/adjust.html", part=part)


@bp.route("/export")
async def export():
    """Export inventory data as CSV."""
    rows = get_inventory_service().export_data()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Part ID", "Part Number", "Manufacturer", "Description", "Category",
        "UoM", "Qty On Hand", "Reorder Point", "Kanban Total",
        "Lead Time (days)", "Last Count Date", "Avg Daily Demand",
        "Days of Supply", "Status",
    ])

    for row in rows:
        part = row["part"]
        writer.writerow([
            part["id"],
            part["part_number"],
            part["manufacturer"],
            part["description"] or "",
            part["category"] or "",
            part["uom_abbr"],
            part["quantity_on_hand"],
            part["total_reorder_point"],
            part["total_kanban_quantity"],
            part["reorder_lead_time_days"],
            part["last_count_date"].isoformat() if part["last_count_date"] else "",
            round(row["avg_daily_demand"], 2),
            round(row["days_of_supply"], 1) if row["days_of_supply"] else "",
            str(row["status"]).upper(),
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                f"attachment; filename=inventory_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )
