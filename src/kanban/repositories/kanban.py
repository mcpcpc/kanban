"""Repository for the ``kanban`` table."""

from sqlite3 import Connection

from kanban.utils.calculations import calculate_number_of_cards


class KanbanRepository:
    def __init__(self, db: Connection) -> None:
        self.db = db

    def find_by_id(self, kanban_id: int):
        return self.db.execute(
            "SELECT * FROM kanban WHERE id = ?", [kanban_id]
        ).fetchone()

    def find_with_details(self, kanban_id: int):
        """Kanban joined with part, location, and UoM."""
        return self.db.execute(
            """SELECT k.*,
                      p.part_number, p.manufacturer, p.description AS part_description,
                      p.reorder_lead_time_days,
                      b.location AS location_name,
                      u.name AS uom_name, u.abbreviation AS uom_abbr,
                      CAST(k.estimated_daily_demand
                           * (p.reorder_lead_time_days + k.safety_lead_time_days) AS INTEGER
                      ) AS reorder_point
               FROM kanban k
               JOIN part p          ON k.part_id     = p.id
               JOIN location b      ON k.location_id = b.id
               JOIN unit_of_measure u ON p.unit_of_measure_id = u.id
               WHERE k.id = ?""",
            [kanban_id],
        ).fetchone()

    def find_with_part_location(self, kanban_id: int):
        """Lighter join used by scan / datawedge look-ups."""
        return self.db.execute(
            """SELECT k.*, p.part_number AS part_name, b.location AS location_name
               FROM kanban k
               JOIN part p     ON k.part_id     = p.id
               JOIN location b ON k.location_id = b.id
               WHERE k.id = ?""",
            [kanban_id],
        ).fetchone()

    def find_all(self, *, search: str = "", status: str = ""):
        query = """
            SELECT k.*, p.part_number AS part_name, p.manufacturer,
                   p.reorder_lead_time_days,
                   b.location AS location_name,
                   CAST(k.estimated_daily_demand
                        * (p.reorder_lead_time_days + k.safety_lead_time_days) AS INTEGER
                   ) AS reorder_point
            FROM kanban k
            JOIN part p     ON k.part_id     = p.id
            JOIN location b ON k.location_id = b.id
            WHERE 1=1
        """
        params: list = []
        if search:
            query += " AND (p.part_number LIKE ? OR p.manufacturer LIKE ? OR b.location LIKE ?)"
            p = f"%{search}%"
            params.extend([p, p, p])
        if status == "active":
            query += " AND k.is_active = 1"
        elif status == "inactive":
            query += " AND k.is_active = 0"
        query += " ORDER BY p.part_number, b.location"
        return self.db.execute(query, params).fetchall()

    def find_by_part_id(self, part_id: int):
        return self.db.execute(
            """SELECT k.*, b.location AS location_name
               FROM kanban k
               JOIN location b ON k.location_id = b.id
               WHERE k.part_id = ?
               ORDER BY b.location""",
            [part_id],
        ).fetchall()

    def find_by_location_id(self, location_id: int):
        return self.db.execute(
            """SELECT k.*, p.part_number AS part_name, p.manufacturer
               FROM kanban k
               JOIN part p ON k.part_id = p.id
               WHERE k.location_id = ?
               ORDER BY p.part_number""",
            [location_id],
        ).fetchall()

    def find_active_by_part_id(self, part_id: int):
        return self.db.execute(
            "SELECT id FROM kanban WHERE part_id = ? AND is_active = 1",
            [part_id],
        ).fetchall()

    def count_active(self) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM kanban WHERE is_active = 1"
        ).fetchone()[0]

    def count_events(self, kanban_id: int) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM kanban_event WHERE kanban_id = ?", [kanban_id]
        ).fetchone()[0]

    def get_most_active(self, limit: int = 10):
        return self.db.execute("""
            SELECT k.id, p.part_number AS part_name, b.location AS location_name,
                   COUNT(*) AS event_count
            FROM kanban_event ke
            JOIN kanban k   ON ke.kanban_id  = k.id
            JOIN part p     ON k.part_id     = p.id
            JOIN location b ON k.location_id = b.id
            GROUP BY k.id
            ORDER BY event_count DESC
            LIMIT ?
        """, [limit]).fetchall()

    def get_30_day_creation_trend(self, since: str):
        return self.db.execute("""
            SELECT date(created_at) AS day, COUNT(*) AS count
            FROM kanban WHERE created_at >= ?
            GROUP BY date(created_at) ORDER BY day
        """, (since,)).fetchall()

    def get_with_lead_time(self, kanban_id: int):
        return self.db.execute("""
            SELECT k.*, p.reorder_lead_time_days
            FROM kanban k
            JOIN part p ON k.part_id = p.id
            WHERE k.id = ?
        """, [kanban_id]).fetchone()

    def create(
        self, *, part_id, location_id, kanban_quantity, safety_lead_time_days,
        estimated_daily_demand, lead_time_days, is_active,
    ) -> int:
        number_of_cards = calculate_number_of_cards(
            estimated_daily_demand, lead_time_days, safety_lead_time_days, kanban_quantity,
        )
        cursor = self.db.execute(
            """INSERT INTO kanban
                   (part_id, location_id, kanban_quantity, safety_lead_time_days,
                    estimated_daily_demand, number_of_cards, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [part_id, location_id, kanban_quantity, safety_lead_time_days,
             estimated_daily_demand, number_of_cards, 1 if is_active else 0],
        )
        self.db.commit()
        return cursor.lastrowid

    def update(
        self, kanban_id: int, *, part_id, location_id, kanban_quantity,
        safety_lead_time_days, estimated_daily_demand, lead_time_days, is_active,
    ) -> None:
        number_of_cards = calculate_number_of_cards(
            estimated_daily_demand, lead_time_days, safety_lead_time_days, kanban_quantity,
        )
        self.db.execute(
            """UPDATE kanban
               SET part_id = ?, location_id = ?, kanban_quantity = ?,
                   safety_lead_time_days = ?, estimated_daily_demand = ?,
                   number_of_cards = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [part_id, location_id, kanban_quantity, safety_lead_time_days,
             estimated_daily_demand, number_of_cards, 1 if is_active else 0, kanban_id],
        )
        self.db.commit()

    def delete(self, kanban_id: int) -> None:
        self.db.execute("DELETE FROM kanban WHERE id = ?", [kanban_id])
        self.db.commit()
