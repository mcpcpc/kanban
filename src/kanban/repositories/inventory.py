"""Repository for the ``inventory`` table."""

from sqlite3 import Connection


class InventoryRepository:
    def __init__(self, db: Connection) -> None:
        self.db = db

    # ── Reads ────────────────────────────────────────────────────────

    def find_all_with_details(self, *, search: str = ""):
        query = """
            SELECT
                p.id,
                p.part_number,
                p.manufacturer,
                p.description,
                p.category,
                p.reorder_lead_time_days,
                u.abbreviation AS uom_abbr,
                COALESCE(i.quantity_on_hand, 0) AS quantity_on_hand,
                i.last_count_date,
                COALESCE(k_agg.total_kanban_quantity, 0) AS total_kanban_quantity,
                COALESCE(k_agg.total_reorder_point, 0) AS total_reorder_point,
                COALESCE(k_agg.kanban_count, 0) AS kanban_count
            FROM part p
            JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
            LEFT JOIN inventory i ON p.id = i.part_id
            LEFT JOIN (
                SELECT
                    part_id,
                    SUM(kanban_quantity) AS total_kanban_quantity,
                    SUM(CAST(estimated_daily_demand
                         * ((SELECT reorder_lead_time_days FROM part
                             WHERE id = kanban.part_id)
                            + safety_lead_time_days) AS INTEGER)
                    ) AS total_reorder_point,
                    COUNT(*) AS kanban_count
                FROM kanban WHERE is_active = 1
                GROUP BY part_id
            ) k_agg ON p.id = k_agg.part_id
            WHERE 1=1
        """
        params: list = []
        if search:
            query += " AND (p.part_number LIKE ? OR p.manufacturer LIKE ? OR p.description LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        query += " ORDER BY p.part_number"
        return self.db.execute(query, params).fetchall()

    # ── Writes ───────────────────────────────────────────────────────

    def upsert(self, part_id: int, quantity: float,
               notes: str | None = None) -> None:
        self.db.execute("""
            INSERT INTO inventory (part_id, quantity_on_hand, last_count_date, notes, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(part_id) DO UPDATE SET
                quantity_on_hand = excluded.quantity_on_hand,
                last_count_date  = CURRENT_TIMESTAMP,
                notes            = excluded.notes,
                updated_at       = CURRENT_TIMESTAMP
        """, [part_id, quantity, notes])

    def decrease_quantity(self, part_id: int, amount: float) -> None:
        self.db.execute("""
            UPDATE inventory
            SET quantity_on_hand = MAX(0, quantity_on_hand - ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE part_id = ?
        """, [amount, part_id])
