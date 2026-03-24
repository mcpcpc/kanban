from os import makedirs
from os.path import join

from quart import Quart

from kanban.db import init_db
from kanban.datawedge import init_datawedge
from kanban.routes import register_blueprints
from kanban.oauth import init_oauth

__version__ = "0.0.1"


def create_app(test_config=None) -> Quart:
    app = Quart(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=join(app.instance_path, "kanban.db"),
        VERSION=__version__
    )

    if test_config is None:
        app.config.from_pyfile(
            "config.py",
            silent=True,
        )
    else:
        app.config.update(test_config)

    try:
        makedirs(app.instance_path)
    except OSError:
        pass

    init_db(app)
    init_oauth(app)
    init_datawedge(app)
    register_blueprints(app)

    return app
