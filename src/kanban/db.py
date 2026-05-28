from datetime import datetime
from os.path import exists
from pathlib import Path
from sqlite3 import connect
from sqlite3 import PARSE_DECLTYPES
from sqlite3 import register_converter
from sqlite3 import Row

from click import command
from click import echo
from click import option
from click import prompt
from quart import current_app
from quart import g
from quart.cli import with_appcontext

register_converter("datetime", lambda v: datetime.fromisoformat(v.decode()))


def get_db():
    """Return the request-scoped database connection, creating one if needed."""
    if not hasattr(g, "db"):
        g.db = connect(
            current_app.config["DATABASE"],
            detect_types=PARSE_DECLTYPES,
        )
        g.db.row_factory = Row
    return g.db


async def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _open_db(path: str):
    db = connect(path, detect_types=PARSE_DECLTYPES)
    db.row_factory = Row
    return db


def run_auth_migration(db_path: str) -> None:
    """Idempotent migration: add auth tables to an existing database."""
    db = _open_db(db_path)
    db.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
                CHECK(role IN ('admin', 'manager', 'user')),
            is_active INTEGER NOT NULL DEFAULT 1,
            last_login_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        db.execute(
            "ALTER TABLE kanban_event ADD COLUMN "
            "user_id INTEGER REFERENCES user(id)"
        )
    except Exception:
        pass  # column already exists
    # Remove username column if present (UNIQUE columns can't be dropped directly)
    cols = [r[1] for r in db.execute("PRAGMA table_info(user)").fetchall()]
    if "username" in cols:
        db.executescript("""
            PRAGMA foreign_keys = OFF;
            CREATE TABLE user_new (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
                    CHECK(role IN ('admin', 'manager', 'user')),
                is_active INTEGER NOT NULL DEFAULT 1,
                last_login_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO user_new
                SELECT id, email, display_name, password_hash,
                       role, is_active, last_login_at, created_at, updated_at
                FROM user;
            DROP TABLE user;
            ALTER TABLE user_new RENAME TO user;
            PRAGMA foreign_keys = ON;
        """)
    db.commit()
    db.close()


@command("init-db")
@with_appcontext
def init_db_command() -> None:
    db = get_db()
    root_path = Path(current_app.root_path)
    with open(root_path / "schema.sql") as file:
        db.executescript(file.read())
    echo("Database initialized.")


@command("create-admin")
@with_appcontext
def create_admin_command() -> None:
    """Create an administrator account."""
    from kanban.repositories.user import UserRepository
    from kanban.services.user import UserService, validate_password

    email = prompt("Email")
    display_name = prompt("Display name")
    password = prompt("Password", hide_input=True, confirmation_prompt=True)

    err = validate_password(password)
    if err:
        echo(f"Error: {err}")
        return

    db = get_db()
    result = UserService(UserRepository(db)).create(
        email=email,
        display_name=display_name,
        password=password,
        role="admin",
    )
    echo(result.message)


def init_db(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin_command)

    # Auto-migrate auth schema for existing databases
    db_path = app.config.get("DATABASE", "")
    if db_path and exists(db_path):
        run_auth_migration(db_path)
