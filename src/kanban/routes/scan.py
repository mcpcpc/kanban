from quart import Blueprint, render_template, request, redirect, url_for, flash

from kanban.db import get_db

bp = Blueprint("scan", __name__, url_prefix="/scan")


@bp.route("/")
async def index():
    """Quick scan interface."""
    return await render_template("scan/quick.html")


@bp.route("/", methods=["POST"])
async def process():
    """Process a scanned barcode."""
    db = get_db()
    form = await request.form
    
    barcode = form.get("barcode", "").strip()
    action = form.get("action", "signal")
    quantity = form.get("quantity", "").strip()
    notes = form.get("notes", "").strip()
    return_to = form.get("return_to", "").strip()
    
    # Determine redirect target
    def get_redirect():
        if return_to:
            return redirect(return_to)
        return redirect(url_for("scan.index"))
    
    if not barcode:
        await flash("No barcode scanned.", "danger")
        return get_redirect()
    
    # Parse kanban ID from barcode (format: K000001)
    kanban_id = None
    if barcode.upper().startswith("K"):
        try:
            kanban_id = int(barcode[1:])
        except ValueError:
            pass
    else:
        try:
            kanban_id = int(barcode)
        except ValueError:
            pass
    
    if not kanban_id:
        await flash(f"Invalid barcode format: {barcode}", "danger")
        return get_redirect()
    
    # Verify kanban exists
    kanban = db.execute(
        """SELECT k.*, p.part_number as part_name, b.location as location_name
           FROM kanban k
           JOIN part p ON k.part_id = p.id
           JOIN location b ON k.location_id = b.id
           WHERE k.id = ?""",
        [kanban_id]
    ).fetchone()
    
    if not kanban:
        await flash(f"Kanban not found: {barcode}", "danger")
        return get_redirect()
    
    if not kanban["is_active"]:
        await flash(f"Kanban is inactive: {kanban['part_name']} @ {kanban['location_name']}", "warning")
        return get_redirect()
    
    # Count open signals: signals minus completed restocks
    open_signal_count = db.execute("""
        SELECT
            (SELECT COUNT(*) FROM kanban_event ke
             JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
             WHERE ke.kanban_id = ? AND ket.type = 'signal')
            -
            (SELECT COUNT(*) FROM kanban_event ke
             JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
             WHERE ke.kanban_id = ? AND ket.type = 'restock_complete')
        AS cnt
    """, [kanban_id, kanban_id]).fetchone()["cnt"]

    # Validate signal action: limit active signals to number_of_cards
    if action == "signal":
        if open_signal_count >= kanban["number_of_cards"]:
            await flash(
                f"All {kanban['number_of_cards']} cards already signaled for "
                f"{kanban['part_name']} @ {kanban['location_name']} — waiting for restock",
                "warning"
            )
            return get_redirect()
    
    # Validate restock actions require an open signal
    if action in ("restock_start", "restock_complete"):
        if open_signal_count <= 0:
            action_label = "start restocking" if action == "restock_start" else "complete restocking"
            await flash(f"Cannot {action_label}: no open signal for {kanban['part_name']} @ {kanban['location_name']}", "danger")
            return get_redirect()
    
    # Get event type ID
    event_type_row = db.execute(
        "SELECT id FROM kanban_event_type WHERE type = ?",
        [action]
    ).fetchone()
    
    if not event_type_row:
        await flash(f"Invalid action: {action}", "danger")
        return get_redirect()
    
    # Parse quantity if provided
    qty = None
    if quantity:
        try:
            qty = int(quantity)
        except ValueError:
            await flash("Invalid quantity.", "danger")
            return get_redirect()
    
    # Record the event
    db.execute(
        """INSERT INTO kanban_event (kanban_id, kanban_event_type, quantity, notes)
           VALUES (?, ?, ?, ?)""",
        [kanban_id, event_type_row["id"], qty, notes or None]
    )
    
    # Decrease inventory on signal (location was depleted)
    if action == "signal":
        db.execute("""
            UPDATE inventory 
            SET quantity_on_hand = MAX(0, quantity_on_hand - ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE part_id = ?
        """, [kanban["kanban_quantity"], kanban["part_id"]])
    
    db.commit()
    
    # Build success message
    action_names = {
        "signal": "Signal recorded",
        "restock_start": "Restock started",
        "restock_complete": "Restock complete",
        "adjustment": "Adjustment recorded"
    }
    
    msg = f"{action_names.get(action, action)}: {kanban['part_name']} @ {kanban['location_name']}"
    if qty is not None:
        msg += f" (qty: {qty})"
    
    await flash(msg, "success")
    return get_redirect()
