"""Authentication decorators and session helpers."""

import time
from functools import wraps

from quart import abort, g, redirect, request, session, url_for

SESSION_TIMEOUT = 8 * 3600  # seconds

# Endpoints accessible without a session
PUBLIC_ENDPOINTS = frozenset({
    "dashboard.index",
    "auth.login",
    "auth.logout",
    "static",
})


def manager_required(f):
    """Allows managers and admins; blocks regular users."""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        if not g.current_user:
            return redirect(url_for("auth.login", next=request.path))
        if g.current_user["role"] not in ("admin", "manager"):
            abort(403)
        return await f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Allows admins only."""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        if not g.current_user:
            return redirect(url_for("auth.login", next=request.path))
        if g.current_user["role"] != "admin":
            abort(403)
        return await f(*args, **kwargs)
    return wrapper


def touch_session() -> bool:
    """Update inactivity timer; return False if session has expired."""
    if "user_id" not in session:
        return False
    last = session.get("_last_active", 0)
    if time.time() - last > SESSION_TIMEOUT:
        session.clear()
        return False
    session["_last_active"] = time.time()
    return True
