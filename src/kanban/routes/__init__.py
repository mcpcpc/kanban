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


def register_blueprints(app) -> None:
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
