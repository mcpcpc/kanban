"""Repository for the ``location`` table."""

from sqlite3 import Connection


class LocationRepository:
    def __init__(self, db: Connection) -> None:
        self.db = db

    def find_by_id(self, location_id: int):
        return self.db.execute(
            "SELECT * FROM location WHERE id = ?", [location_id]
        ).fetchone()

    def find_all(self, *, search: str = "", color: str = ""):
        query = "SELECT * FROM location WHERE 1=1"
        params: list = []
        if search:
            query += " AND (location LIKE ? OR description LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s])
        if color:
            query += " AND color = ?"
            params.append(color)
        query += " ORDER BY location"
        return self.db.execute(query, params).fetchall()

    def count_all(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM location").fetchone()[0]

    def count_kanbans(self, location_id: int) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM kanban WHERE location_id = ?", [location_id]
        ).fetchone()[0]

    def get_kanban_counts(self) -> dict[int, int]:
        rows = self.db.execute("""
            SELECT location_id, COUNT(*) AS cnt
            FROM kanban WHERE is_active = 1
            GROUP BY location_id
        """).fetchall()
        return {row["location_id"]: row["cnt"] for row in rows}

    def get_colors_in_use(self) -> list[str]:
        rows = self.db.execute(
            "SELECT DISTINCT color FROM location WHERE color IS NOT NULL ORDER BY color"
        ).fetchall()
        return [row["color"] for row in rows]

    def get_30_day_creation_trend(self, since: str):
        return self.db.execute("""
            SELECT date(created_at) AS day, COUNT(*) AS count
            FROM location WHERE created_at >= ?
            GROUP BY date(created_at) ORDER BY day
        """, (since,)).fetchall()

    def create(self, *, location: str, description: str | None = None,
               color: str | None = None) -> int:
        cursor = self.db.execute(
            "INSERT INTO location (location, description, color) VALUES (?, ?, ?)",
            [location, description, color],
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, location_id: int, *, location: str,
               description: str | None = None, color: str | None = None) -> None:
        self.db.execute(
            """UPDATE location SET location = ?, description = ?, color = ?,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            [location, description, color, location_id],
        )
        self.db.commit()

    def delete(self, location_id: int) -> None:
        self.db.execute("DELETE FROM location WHERE id = ?", [location_id])
        self.db.commit()
