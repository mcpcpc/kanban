"""Repository for the ``setting`` table."""

from sqlite3 import Connection


class SettingRepository:
    def __init__(self, db: Connection) -> None:
        self.db = db

    def get(self):
        return self.db.execute("SELECT * FROM setting LIMIT 1").fetchone()

    def update(self, *, printer_hostname: str, printer_port: int,
               printer_timeout_seconds: float, label_template: str) -> None:
        self.db.execute(
            """UPDATE setting
               SET printer_hostname = ?, printer_port = ?,
                   printer_timeout_seconds = ?, label_template = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = 1""",
            (printer_hostname, printer_port, printer_timeout_seconds, label_template),
        )
        self.db.commit()
