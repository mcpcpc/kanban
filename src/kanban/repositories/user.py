"""Repository for the ``user`` table."""

from sqlite3 import Connection


class UserRepository:
    def __init__(self, db: Connection) -> None:
        self.db = db

    def find_by_id(self, user_id: int):
        return self.db.execute(
            "SELECT * FROM user WHERE id = ?", [user_id]
        ).fetchone()

    def find_by_email(self, email: str):
        return self.db.execute(
            "SELECT * FROM user WHERE email = ? COLLATE NOCASE", [email]
        ).fetchone()

    def find_all(self):
        return self.db.execute(
            "SELECT * FROM user ORDER BY display_name"
        ).fetchall()

    def count_admins(self) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM user WHERE role = 'admin' AND is_active = 1"
        ).fetchone()[0]

    def create(self, *, email, display_name, password_hash,
               role="user", is_active=1) -> int:
        cursor = self.db.execute(
            """INSERT INTO user (email, display_name, password_hash, role, is_active)
               VALUES (?, ?, ?, ?, ?)""",
            [email, display_name, password_hash, role, is_active],
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, user_id: int, *, email, display_name, role, is_active) -> None:
        self.db.execute(
            """UPDATE user
               SET email = ?, display_name = ?, role = ?, is_active = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [email, display_name, role, is_active, user_id],
        )
        self.db.commit()

    def update_password(self, user_id: int, password_hash: str) -> None:
        self.db.execute(
            """UPDATE user SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [password_hash, user_id],
        )
        self.db.commit()

    def update_last_login(self, user_id: int) -> None:
        self.db.execute(
            "UPDATE user SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?",
            [user_id],
        )
        self.db.commit()
