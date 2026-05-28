"""Repository for ``kanban_event`` and ``kanban_event_type`` tables."""

from datetime import datetime
from sqlite3 import Connection

from kanban.enums import EventType


class EventRepository:
    def __init__(self, db: Connection) -> None:
        self.db = db

    def get_event_type_id(self, event_type: EventType) -> int | None:
        row = self.db.execute(
            "SELECT id FROM kanban_event_type WHERE type = ?", [event_type.value]
        ).fetchone()
        return row["id"] if row else None

    def get_all_event_types(self):
        return self.db.execute(
            "SELECT * FROM kanban_event_type ORDER BY type"
        ).fetchall()

    def get_open_signal_count(self, kanban_id: int) -> int:
        row = self.db.execute(
            """SELECT
                   (SELECT COUNT(*) FROM kanban_event ke
                    JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                    WHERE ke.kanban_id = ? AND ket.type = ?)
                   -
                   (SELECT COUNT(*) FROM kanban_event ke
                    JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                    WHERE ke.kanban_id = ? AND ket.type = ?)
               AS cnt""",
            [kanban_id, EventType.SIGNAL, kanban_id, EventType.RESTOCK_COMPLETE],
        ).fetchone()
        return row["cnt"]

    def get_pending_signals(self):
        return self.db.execute("""
            SELECT * FROM (
                SELECT
                    k.id AS kanban_id,
                    p.part_number AS part_name,
                    p.manufacturer,
                    b.location AS location_name,
                    (
                        SELECT COUNT(*) FROM kanban_event ke
                        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                        WHERE ke.kanban_id = k.id AND ket.type = ?
                    ) - (
                        SELECT COUNT(*) FROM kanban_event ke
                        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                        WHERE ke.kanban_id = k.id AND ket.type = ?
                    ) AS pending_count,
                    (
                        SELECT MAX(ke.created_at) FROM kanban_event ke
                        JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
                        WHERE ke.kanban_id = k.id AND ket.type = ?
                    ) AS signal_time
                FROM kanban k
                JOIN part p     ON k.part_id     = p.id
                JOIN location b ON k.location_id = b.id
                WHERE k.is_active = 1
            ) WHERE pending_count > 0
            ORDER BY signal_time ASC
        """, [EventType.SIGNAL, EventType.RESTOCK_COMPLETE, EventType.SIGNAL]).fetchall()

    def create(self, kanban_id: int, event_type_id: int,
               quantity: int | None = None, notes: str | None = None,
               user_id: int | None = None) -> int:
        cursor = self.db.execute(
            """INSERT INTO kanban_event
                   (kanban_id, kanban_event_type, user_id, quantity, notes)
               VALUES (?, ?, ?, ?, ?)""",
            [kanban_id, event_type_id, user_id, quantity, notes],
        )
        return cursor.lastrowid

    def find_by_kanban_id(self, kanban_id: int, limit: int = 20):
        return self.db.execute(
            """SELECT ke.*, ket.type AS event_type
               FROM kanban_event ke
               JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
               WHERE ke.kanban_id = ?
               ORDER BY ke.created_at DESC
               LIMIT ?""",
            [kanban_id, limit],
        ).fetchall()

    def find_recent_with_details(self, limit: int = 10):
        return self.db.execute("""
            SELECT ke.id, ke.created_at, ke.quantity, ke.notes,
                   ket.type AS event_type,
                   k.id AS kanban_id,
                   p.part_number AS part_name,
                   b.location AS location_name
            FROM kanban_event ke
            JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
            JOIN kanban k   ON ke.kanban_id  = k.id
            JOIN part p     ON k.part_id     = p.id
            JOIN location b ON k.location_id = b.id
            ORDER BY ke.created_at DESC
            LIMIT ?
        """, [limit]).fetchall()

    def find_all_with_details(
        self, *, search: str = "", event_type: str = "",
        kanban_id: str = "", limit: int = 100,
    ):
        query = """
            SELECT ke.id, ke.created_at, ke.quantity, ke.notes,
                   ket.type AS event_type,
                   k.id AS kanban_id,
                   p.id AS part_id,
                   p.part_number AS part_name,
                   p.manufacturer,
                   b.location AS location_name
            FROM kanban_event ke
            JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
            JOIN kanban k   ON ke.kanban_id  = k.id
            JOIN part p     ON k.part_id     = p.id
            JOIN location b ON k.location_id = b.id
            WHERE 1=1
        """
        params: list = []
        if search:
            query += (" AND (p.part_number LIKE ? OR p.manufacturer LIKE ?"
                      " OR b.location LIKE ? OR ke.notes LIKE ?)")
            s = f"%{search}%"
            params.extend([s, s, s, s])
        if event_type:
            query += " AND ket.type = ?"
            params.append(event_type)
        if kanban_id:
            query += " AND k.id = ?"
            params.append(kanban_id)
        query += " ORDER BY ke.created_at DESC LIMIT ?"
        params.append(limit)
        return self.db.execute(query, params).fetchall()

    def count_all(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM kanban_event").fetchone()[0]

    def count_by_type(self):
        return self.db.execute("""
            SELECT ket.type, COUNT(*) AS count
            FROM kanban_event ke
            JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
            GROUP BY ket.id ORDER BY count DESC
        """).fetchall()

    def get_cycle_times(self):
        return self.db.execute("""
            SELECT ke_signal.kanban_id,
                   julianday(ke_complete.created_at)
                   - julianday(ke_signal.created_at) AS days
            FROM kanban_event ke_signal
            JOIN kanban_event_type ket_signal
                 ON ke_signal.kanban_event_type = ket_signal.id
            JOIN kanban_event ke_complete
                 ON ke_complete.kanban_id = ke_signal.kanban_id
            JOIN kanban_event_type ket_complete
                 ON ke_complete.kanban_event_type = ket_complete.id
            WHERE ket_signal.type   = ?
              AND ket_complete.type = ?
              AND ke_complete.created_at > ke_signal.created_at
              AND NOT EXISTS (
                  SELECT 1 FROM kanban_event ke2
                  JOIN kanban_event_type ket2 ON ke2.kanban_event_type = ket2.id
                  WHERE ke2.kanban_id = ke_signal.kanban_id
                    AND ket2.type IN (?, ?)
                    AND ke2.created_at > ke_signal.created_at
                    AND ke2.created_at < ke_complete.created_at
              )
        """, [EventType.SIGNAL, EventType.RESTOCK_COMPLETE,
              EventType.SIGNAL, EventType.RESTOCK_COMPLETE]).fetchall()

    def get_30_day_signal_trend(self, since: str):
        return self.db.execute("""
            SELECT date(ke.created_at) AS day, COUNT(*) AS count
            FROM kanban_event ke
            JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
            WHERE ket.type = ? AND ke.created_at >= ?
            GROUP BY date(ke.created_at) ORDER BY day
        """, (EventType.SIGNAL, since)).fetchall()

    def get_demand_total(self, part_id: int, since_date: datetime) -> int:
        result = self.db.execute(
            """SELECT COALESCE(SUM(ke.quantity), 0) AS total_restocked
               FROM kanban_event ke
               JOIN kanban_event_type ket ON ke.kanban_event_type = ket.id
               JOIN kanban k ON ke.kanban_id = k.id
               WHERE k.part_id = ?
                 AND ket.type = ?
                 AND ke.created_at >= ?
                 AND ke.quantity IS NOT NULL""",
            [part_id, EventType.RESTOCK_COMPLETE, since_date],
        ).fetchone()
        return result["total_restocked"] if result else 0
