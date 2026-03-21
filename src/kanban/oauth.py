from functools import wraps

from quart import session
from quart import url_for
from quart import Quart
from quart import redirect
from quart import render_template
from quart import request
from quart_authlib import OAuth


def authorize(view):
    @wraps(view)
    async def wrapper(*args, **kwargs):
        if session.get("user"):
            return await view(*args, **kwargs)
        return redirect(url_for("login"))

    return wrapper


def init_oauth(app: Quart) -> Quart:
    oauth = OAuth(app)
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    @app.route("/login")
    async def login():
        return await render_template("login.html")

    @app.route("/login/google")
    async def login_google():
        redirect_uri = url_for("authorize", _external=True)
        return oauth.google.authorize_redirect(redirect_uri)

    @app.route("/auth")
    async def authorize():
        token = await oauth.google.authorize_access_token()
        session["user"] = token["userinfo"]
        return redirect(url_for("index"))

    @app.route("/logout")
    async def logout():
        session.pop("user", None)
        return redirect(url_for("login"))

    return app
