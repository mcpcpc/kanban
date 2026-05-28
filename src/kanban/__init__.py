from datetime import timedelta
from os import makedirs
from os.path import join

from quart import g, redirect, request, session, url_for, Quart

from kanban.auth import PUBLIC_ENDPOINTS, touch_session
from kanban.db import init_db
from kanban.datawedge import init_datawedge
from kanban.routes.auth import bp as auth_bp
from kanban.routes.dashboard import bp as dashboard_bp
from kanban.routes.events import bp as events_bp
from kanban.routes.help import bp as help_bp
from kanban.routes.inventory import bp as inventory_bp
from kanban.routes.kanbans import bp as kanbans_bp
from kanban.routes.locations import bp as locations_bp
from kanban.routes.parts import bp as parts_bp
from kanban.routes.reports import bp as reports_bp
from kanban.routes.scan import bp as scan_bp
from kanban.routes.settings import bp as settings_bp
from kanban.routes.users import bp as users_bp

__version__ = "0.0.1"


def create_app(test_config=None) -> Quart:
    """Application factory — creates and configures the Quart app."""
    app = Quart(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=join(app.instance_path, "kanban.db"),
        DATAWEDGE_HOST="0.0.0.0",
        DATAWEDGE_PORT=58627,
        VERSION=__version__,
        PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.update(test_config)

    try:
        makedirs(app.instance_path)
    except OSError:
        pass

    init_db(app)
    init_datawedge(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(kanbans_bp)
    app.register_blueprint(locations_bp)
    app.register_blueprint(parts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(scan_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(users_bp)

    @app.before_request
    async def _auth_gate():
        from kanban.deps import get_user_repo

        # Refresh inactivity timer; clear expired sessions
        if "user_id" in session:
            if not touch_session():
                g.current_user = None
                ep = request.endpoint
                if ep and ep not in PUBLIC_ENDPOINTS:
                    return redirect(url_for("auth.login", next=request.path))
                return

        # Load current user into g
        g.current_user = None
        if "user_id" in session:
            user = get_user_repo().find_by_id(session["user_id"])
            if user and user["is_active"]:
                g.current_user = user
            else:
                session.clear()

        # Gate non-public endpoints
        ep = request.endpoint
        if ep and ep not in PUBLIC_ENDPOINTS and not ep.startswith("static"):
            if not g.current_user:
                return redirect(url_for("auth.login", next=request.path))

    @app.errorhandler(403)
    async def forbidden(_):
        return (
            await app.make_response(
                (
                    "<h1>403 — Access Denied</h1>"
                    "<p>You don't have permission to access this page.</p>"
                    f'<a href="{url_for("dashboard.index")}">Go home</a>',
                    403,
                )
            )
        )

    return app
