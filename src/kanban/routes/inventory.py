from quart import Blueprint, render_template, request, redirect, url_for, flash, Response
import csv
import io
from datetime import datetime, timedelta

from kanban.db import get_db

bp = Blueprint("inventory", __name__, url_prefix="/inventory")

ITEMS_PER_PAGE = 20


def calculate_demand_stats(db, part_id, days=30):
    """Calculate average daily demand based on restock events."""
    since_date = datetime.now() - timedelta(days=days)
    
    # Get total restocked quantity in the period
    result = db.execute("""
        SELECT COALESCE(SUM(ke.quantity), 0) as total_restocked
        FROM kanban_event ke
        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
        JOIN kanban k ON ke.kanban_id = k.id
        WHERE k.part_id = ?
        AND ket.type = 'restock_complete'
        AND ke.created_at >= ?
        AND ke.quantity IS NOT NULL
    """, [part_id, since_date]).fetchone()
    
    total_restocked = result["total_restocked"] if result else 0
    avg_daily_demand = total_restocked / days if days > 0 else 0
    
    return {
        "total_restocked": total_restocked,
        "avg_daily_demand": avg_daily_demand,
        "period_days": days
    }


@bp.route("/")
async def index():
    """Inventory list with stock levels and demand metrics."""
    db = get_db()
    
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    page = max(1, page)
    
    # Get all parts with their inventory and kanban info
    query = """
        SELECT 
            p.id,
            p.part_number,
            p.manufacturer,
            p.description,
            p.category,
            p.reorder_lead_time_days,
            u.abbreviation as uom_abbr,
            COALESCE(i.quantity_on_hand, 0) as quantity_on_hand,
            i.last_count_date,
            COALESCE(k_agg.total_kanban_quantity, 0) as total_kanban_quantity,
            COALESCE(k_agg.total_reorder_point, 0) as total_reorder_point,
            COALESCE(k_agg.kanban_count, 0) as kanban_count
        FROM part p
        JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
        LEFT JOIN inventory i ON p.id = i.part_id
        LEFT JOIN (
            SELECT 
                part_id,
                SUM(kanban_quantity) as total_kanban_quantity,
                SUM(CAST(estimated_daily_demand * ((SELECT reorder_lead_time_days FROM part WHERE id = kanban.part_id) + safety_lead_time_days) AS INTEGER)) as total_reorder_point,
                COUNT(*) as kanban_count
            FROM kanban
            WHERE is_active = 1
            GROUP BY part_id
        ) k_agg ON p.id = k_agg.part_id
        WHERE 1=1
    """
    params = []
    
    if search:
        query += " AND (p.part_number LIKE ? OR p.manufacturer LIKE ? OR p.description LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
    
    query += " ORDER BY p.part_number"
    
    parts = db.execute(query, params).fetchall()
    
    # Calculate demand stats for each part and apply status filter
    inventory_data = []
    for part in parts:
        stats = calculate_demand_stats(db, part["id"])
        
        days_of_supply = None
        if stats["avg_daily_demand"] > 0:
            days_of_supply = part["quantity_on_hand"] / stats["avg_daily_demand"]
        
        # Determine status based on kanban reorder points
        status = "ok"
        if part["quantity_on_hand"] <= 0:
            status = "out"
        elif part["total_reorder_point"] > 0 and part["quantity_on_hand"] <= part["total_reorder_point"]:
            status = "low"
        elif days_of_supply is not None and days_of_supply <= part["reorder_lead_time_days"]:
            status = "warning"
        
        # Apply status filter
        if status_filter and status != status_filter:
            continue
        
        inventory_data.append({
            "part": part,
            "avg_daily_demand": stats["avg_daily_demand"],
            "days_of_supply": days_of_supply,
            "status": status,
            "total_kanban_quantity": part["total_kanban_quantity"],
            "total_reorder_point": part["total_reorder_point"]
        })
    
    # Pagination after filtering
    total_count = len(inventory_data)
    total_pages = (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total_count > 0 else 1
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    paginated_data = inventory_data[start_idx:end_idx]
    
    return await render_template(
        "inventory/index.html",
        inventory_data=paginated_data,
        search=search,
        status_filter=status_filter,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )


@bp.route("/<int:part_id>/adjust", methods=["GET", "POST"])
async def adjust(part_id):
    """Adjust inventory quantity for a part."""
    db = get_db()
    
    part = db.execute("""
        SELECT p.*, u.abbreviation as uom_abbr, 
               COALESCE(i.quantity_on_hand, 0) as quantity_on_hand
        FROM part p
        JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
        LEFT JOIN inventory i ON p.id = i.part_id
        WHERE p.id = ?
    """, [part_id]).fetchone()
    
    if not part:
        await flash("Part not found.", "danger")
        return redirect(url_for("inventory.index"))
    
    if request.method == "POST":
        form = await request.form
        adjustment_type = form.get("adjustment_type", "set")
        quantity = form.get("quantity", "0")
        reason = form.get("reason", "").strip()
        
        try:
            quantity = float(quantity)
        except ValueError:
            await flash("Invalid quantity.", "danger")
            return redirect(url_for("inventory.adjust", part_id=part_id))
        
        if adjustment_type == "set":
            new_quantity = quantity
        elif adjustment_type == "add":
            new_quantity = part["quantity_on_hand"] + quantity
        elif adjustment_type == "subtract":
            new_quantity = part["quantity_on_hand"] - quantity
        else:
            new_quantity = quantity
        
        # Ensure non-negative
        new_quantity = max(0, new_quantity)
        
        # Update or insert inventory record
        db.execute("""
            INSERT INTO inventory (part_id, quantity_on_hand, last_count_date, notes, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(part_id) DO UPDATE SET
                quantity_on_hand = excluded.quantity_on_hand,
                last_count_date = CURRENT_TIMESTAMP,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
        """, [part_id, new_quantity, reason or None])
        
        # Also record as an adjustment event for any related kanbans
        kanbans = db.execute(
            "SELECT id FROM kanban WHERE part_id = ? AND is_active = 1", [part_id]
        ).fetchall()
        
        adjustment_type_id = db.execute(
            "SELECT id FROM kanban_event_type WHERE type = 'adjustment'"
        ).fetchone()["id"]
        
        adjustment_qty = new_quantity - part["quantity_on_hand"]
        for kanban in kanbans:
            db.execute("""
                INSERT INTO kanban_event (kanban_id, kanban_event_type, quantity, notes)
                VALUES (?, ?, ?, ?)
            """, [kanban["id"], adjustment_type_id, adjustment_qty, 
                  f"Inventory adjustment: {reason}" if reason else "Inventory adjustment"])
        
        db.commit()
        
        await flash(f"Inventory updated: {part['part_number']} now has {new_quantity} {part['uom_abbr']}.", "success")
        return redirect(url_for("inventory.index"))
    
    return await render_template("inventory/adjust.html", part=part)


@bp.route("/export")
async def export():
    """Export inventory data as CSV."""
    db = get_db()
    
    parts = db.execute("""
        SELECT 
            p.id,
            p.part_number,
            p.manufacturer,
            p.description,
            p.category,
            p.reorder_lead_time_days,
            u.abbreviation as uom_abbr,
            COALESCE(i.quantity_on_hand, 0) as quantity_on_hand,
            i.last_count_date,
            COALESCE(k_agg.total_kanban_quantity, 0) as total_kanban_quantity,
            COALESCE(k_agg.total_reorder_point, 0) as total_reorder_point
        FROM part p
        JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
        LEFT JOIN inventory i ON p.id = i.part_id
        LEFT JOIN (
            SELECT 
                part_id,
                SUM(kanban_quantity) as total_kanban_quantity,
                SUM(CAST(estimated_daily_demand * ((SELECT reorder_lead_time_days FROM part WHERE id = kanban.part_id) + safety_lead_time_days) AS INTEGER)) as total_reorder_point
            FROM kanban
            WHERE is_active = 1
            GROUP BY part_id
        ) k_agg ON p.id = k_agg.part_id
        ORDER BY p.part_number
    """).fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Part ID", "Part Number", "Manufacturer", "Description", "Category",
        "UoM", "Qty On Hand", "Reorder Point", "Kanban Total",
        "Lead Time (days)", "Last Count Date", "Avg Daily Demand", "Days of Supply", "Status"
    ])
    
    for part in parts:
        stats = calculate_demand_stats(db, part["id"])
        
        days_of_supply = None
        if stats["avg_daily_demand"] > 0:
            days_of_supply = part["quantity_on_hand"] / stats["avg_daily_demand"]
        
        status = "OK"
        if part["quantity_on_hand"] <= 0:
            status = "OUT"
        elif part["total_reorder_point"] > 0 and part["quantity_on_hand"] <= part["total_reorder_point"]:
            status = "LOW"
        elif days_of_supply is not None and days_of_supply <= part["reorder_lead_time_days"]:
            status = "WARNING"
        
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
            round(stats["avg_daily_demand"], 2),
            round(days_of_supply, 1) if days_of_supply else "",
            status
        ])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inventory_{datetime.now().strftime('%Y%m%d')}.csv"}
    )
