"""Repository for the ``part`` table."""

from sqlite3 import Connection, IntegrityError


class PartRepository:
    def __init__(self, db: Connection) -> None:
        self.db = db

    def find_by_id(self, part_id: int):
        return self.db.execute(
            "SELECT * FROM part WHERE id = ?", [part_id]
        ).fetchone()

    def find_with_uom(self, part_id: int):
        return self.db.execute(
            """SELECT p.*, u.name AS uom_name, u.abbreviation AS uom_abbr
               FROM part p
               JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
               WHERE p.id = ?""",
            [part_id],
        ).fetchone()

    def find_with_inventory(self, part_id: int):
        return self.db.execute("""
            SELECT p.*, u.abbreviation AS uom_abbr,
                   COALESCE(i.quantity_on_hand, 0) AS quantity_on_hand
            FROM part p
            JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
            LEFT JOIN inventory i ON p.id = i.part_id
            WHERE p.id = ?
        """, [part_id]).fetchone()

    def find_all(self, *, search: str = "", category: str = "",
                 page: int = 1, per_page: int = 20):
        query = """
            SELECT p.*, u.name AS uom_name, u.abbreviation AS uom_abbr
            FROM part p
            JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
            WHERE 1=1
        """
        params: list = []
        if search:
            query += " AND (p.part_number LIKE ? OR p.manufacturer LIKE ? OR p.description LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        if category:
            query += " AND p.category = ?"
            params.append(category)

        count_query = query.replace(
            "SELECT p.*, u.name AS uom_name, u.abbreviation AS uom_abbr",
            "SELECT COUNT(*)",
        )
        total_count = self.db.execute(count_query, params).fetchone()[0]

        query += " ORDER BY p.part_number LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        rows = self.db.execute(query, params).fetchall()
        return rows, total_count

    def count_all(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM part").fetchone()[0]

    def count_kanbans(self, part_id: int) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM kanban WHERE part_id = ?", [part_id]
        ).fetchone()[0]

    def get_categories(self):
        return self.db.execute(
            "SELECT DISTINCT category FROM part "
            "WHERE category IS NOT NULL AND category != '' ORDER BY category"
        ).fetchall()

    def get_lead_time(self, part_id: int) -> float:
        row = self.db.execute(
            "SELECT reorder_lead_time_days FROM part WHERE id = ?", [part_id]
        ).fetchone()
        return row["reorder_lead_time_days"] if row else 7.0

    def get_30_day_creation_trend(self, since: str):
        return self.db.execute("""
            SELECT date(created_at) AS day, COUNT(*) AS count
            FROM part WHERE created_at >= ?
            GROUP BY date(created_at) ORDER BY day
        """, (since,)).fetchall()

    def get_units_of_measure(self):
        return self.db.execute(
            "SELECT * FROM unit_of_measure ORDER BY name"
        ).fetchall()

    def create(self, *, part_number, manufacturer, description=None,
               category=None, datasheet=None, unit_of_measure_id,
               reorder_lead_time_days=7.0):
        """Returns the new row ID.  Raises ``IntegrityError`` on dupe."""
        cursor = self.db.execute(
            """INSERT INTO part (part_number, manufacturer, description, category,
                   datasheet, unit_of_measure_id, reorder_lead_time_days)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [part_number, manufacturer, description, category,
             datasheet, unit_of_measure_id, reorder_lead_time_days],
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, part_id: int, *, part_number, manufacturer,
               description=None, category=None, datasheet=None,
               unit_of_measure_id, reorder_lead_time_days=7.0):
        """Raises ``IntegrityError`` on duplicate part_number."""
        self.db.execute(
            """UPDATE part
               SET part_number = ?, manufacturer = ?, description = ?,
                   category = ?, datasheet = ?, unit_of_measure_id = ?,
                   reorder_lead_time_days = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [part_number, manufacturer, description, category,
             datasheet, unit_of_measure_id, reorder_lead_time_days, part_id],
        )
        self.db.commit()

    def delete(self, part_id: int) -> None:
        self.db.execute("DELETE FROM part WHERE id = ?", [part_id])
        self.db.commit()
