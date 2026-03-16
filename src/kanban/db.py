from datetime import datetime
from pathlib import Path
from sqlite3 import connect
from sqlite3 import PARSE_DECLTYPES
from sqlite3 import register_converter
from sqlite3 import Row

from click import command
from click import echo
from quart import current_app
from quart import g
from quart.cli import with_appcontext


def convert_datetime(value: bytes):
    return datetime.fromisoformat(value.decode())


def get_db():
    if not hasattr(g, "db"):
        register_converter("datetime", convert_datetime)
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


@command("init-db")
@with_appcontext
def init_db_command() -> None:
    db = get_db()
    root_path = Path(current_app.root_path)
    with open(root_path / "schema.sql") as file:
        db.executescript(file.read())
    echo("Database initialized.")


def init_db(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
