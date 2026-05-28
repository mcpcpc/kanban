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
