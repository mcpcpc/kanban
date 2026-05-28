"""Service for user authentication and management."""

import re
import secrets
from sqlite3 import IntegrityError

from werkzeug.security import check_password_hash, generate_password_hash

from kanban.repositories.user import UserRepository
from kanban.services import ServiceResult


def validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[a-z]", password):
        return "Password must include a lowercase letter."
    if not re.search(r"[A-Z]", password):
        return "Password must include an uppercase letter."
    if not re.search(r"\d", password):
        return "Password must include a number."
    return None


class UserService:
    ROLES = ("admin", "manager", "user")

    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    def authenticate(self, email: str, password: str):
        """Return the user row if credentials are valid and account active, else None."""
        user = self.user_repo.find_by_email(email.strip())
        if not user or not user["is_active"]:
            return None
        if not check_password_hash(user["password_hash"], password):
            return None
        self.user_repo.update_last_login(user["id"])
        return user

    def list(self):
        return self.user_repo.find_all()

    def get_by_id(self, user_id: int):
        return self.user_repo.find_by_id(user_id)

    def create(self, *, email, display_name, role="user") -> ServiceResult:
        token = secrets.token_urlsafe(32)
        try:
            user_id = self.user_repo.create(
                email=email.strip().lower(),
                display_name=display_name.strip(),
                password_hash=generate_password_hash(secrets.token_hex(32)),
                role=role,
                must_change_password=1,
                password_reset_token=token,
            )
        except IntegrityError:
            return ServiceResult(False, "Email is already in use.", "danger")
        return ServiceResult(
            True,
            f"User '{email}' created.",
            data={"token": token, "user_id": user_id},
        )

    def generate_reset_link(self, user_id: int) -> ServiceResult:
        user = self.user_repo.find_by_id(user_id)
        if not user:
            return ServiceResult(False, "User not found.", "danger")
        token = secrets.token_urlsafe(32)
        self.user_repo.set_reset_token(user_id, token)
        return ServiceResult(True, "Reset link generated.", data={"token": token})

    def activate_with_token(self, token: str, password: str) -> ServiceResult:
        error = validate_password(password)
        if error:
            return ServiceResult(False, error, "danger")
        user = self.user_repo.find_by_reset_token(token)
        if not user:
            return ServiceResult(False, "This link is invalid or has already been used.", "danger")
        self.user_repo.update_password(user["id"], generate_password_hash(password))
        self.user_repo.clear_reset_token(user["id"])
        return ServiceResult(True, "Password set. Welcome!", data={"user_id": user["id"]})

    def update(self, user_id: int, *, email, display_name, role,
               is_active) -> ServiceResult:
        user = self.user_repo.find_by_id(user_id)
        if user and user["role"] == "admin":
            losing_admin = role != "admin" or not int(is_active)
            if losing_admin and self.user_repo.count_admins() <= 1:
                return ServiceResult(
                    False,
                    "Cannot demote or deactivate the last active admin.",
                    "danger",
                )
        try:
            self.user_repo.update(
                user_id,
                email=email.strip().lower(),
                display_name=display_name.strip(),
                role=role,
                is_active=int(is_active),
            )
        except IntegrityError:
            return ServiceResult(False, "Email is already in use.", "danger")
        return ServiceResult(True, f"User '{email}' updated.")

    def set_password(self, user_id: int, password: str) -> ServiceResult:
        error = validate_password(password)
        if error:
            return ServiceResult(False, error, "danger")
        self.user_repo.update_password(user_id, generate_password_hash(password))
        return ServiceResult(True, "Password updated.")
