"""example_app.auth — authentication backend for the Kibrary admin panel."""
from nuru import DatabaseAuthBackend, db_permission_checker
from .db import get_session
from .models import StaffUser

auth_backend = DatabaseAuthBackend(
    user_model=StaffUser,
    session_factory=get_session,
    username_field="email",
    password_field="password",
    secret_key="dev-secret-key-change-in-production",
    extra_fields=["name", "role"],
)

permission_checker = db_permission_checker

