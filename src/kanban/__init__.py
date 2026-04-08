from os import makedirs
from os.path import join

from quart import Quart

from kanban.db import init_db
from kanban.datawedge import init_datawedge
from kanban.routes.dashboard import bp as dashboard_bp
from kanban.routes.parts import bp as parts_bp
from kanban.routes.locations import bp as locations_bp
from kanban.routes.kanbans import bp as kanbans_bp
from kanban.routes.events import bp as events_bp
from kanban.routes.scan import bp as scan_bp
from kanban.routes.reports import bp as reports_bp
from kanban.routes.inventory import bp as inventory_bp
from kanban.routes.help import bp as help_bp
from kanban.routes.api import bp as api_bp
from kanban.routes.settings import bp as settings_bp

__version__ = "0.0.1"


def create_app(test_config=None) -> Quart:
    app = Quart(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=join(app.instance_path, "kanban.db"),
        DATAWEDGE_HOST="0.0.0.0",
        DATAWEDGE_PORT=58627,
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
    init_datawedge(app)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(parts_bp)
    app.register_blueprint(locations_bp)
    app.register_blueprint(kanbans_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(scan_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)

    return app
