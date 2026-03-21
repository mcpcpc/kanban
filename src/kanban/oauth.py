from functools import wraps

from quart import session
from quart import url_for
from quart import Quart
from quart import redirect
from quart_authlib import OAuth


def init_oauth(app: Quart) -> Quart:
    oauth = OAuth(app)
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    @app.route("/login")
    async def login():
        redirect_uri = url_for("auth", _external=True)
        return oauth.google.authorize_redirect(redirect_uri)

    @app.route("/auth")
    async def auth():
        token = await oauth.google.authorize_access_token()
        session["user"] = token["userinfo"]
        return redirect(url_for("dashboard.index"))

    @app.route("/logout")
    async def logout():
        session.pop("user", None)
        return redirect(url_for("dashboard.index"))

    return app


def authorize(view):
    """Authorization wrapper method."""

    @wraps(view)
    async def wrapper(*args, **kwargs):
        if session.get("user"):
            return await view(*args, **kwargs)
        return redirect(url_for("login"))

    return wrapper
