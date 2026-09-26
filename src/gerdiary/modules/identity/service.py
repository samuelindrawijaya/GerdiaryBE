from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import current_app, request

from gerdiary.extensions import db
from gerdiary.modules.identity import domain
from gerdiary.modules.identity.models import User

_hasher = PasswordHasher()
COOKIE_NAME = "session_token"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def issue_token(user_id: str, issued_at: datetime | None = None) -> str:
    now = issued_at or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(domain.access_token_expiry(now).timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"]
        )
    except jwt.InvalidTokenError:
        return None
    try:
        UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        return None
    return payload


def set_session_cookie(response: Any, token: str) -> None:
    secure = bool(current_app.config.get("SESSION_COOKIE_SECURE", True))
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(domain.ACCESS_TOKEN_LIFETIME.total_seconds()),
        httponly=True,
        samesite="Lax",
        secure=secure,
        path="/",
    )


def clear_session_cookie(response: Any) -> None:
    secure = bool(current_app.config.get("SESSION_COOKIE_SECURE", True))
    response.set_cookie(
        COOKIE_NAME,
        "",
        expires=0,
        max_age=0,
        httponly=True,
        samesite="Lax",
        secure=secure,
        path="/",
    )


def current_user() -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    user = db.session.get(User, payload["sub"])
    if user is None or user.deleted_at is not None:
        return None
    return user


def register_user(
    email_raw: str, password: str, name: str | None, journal_theme: str = "kawaii"
) -> User:
    email = domain.validate_email(email_raw)
    domain.validate_password(password)

    existing = db.session.query(User).filter(User.email == email).one_or_none()
    if existing is not None:
        raise domain.EmailAlreadyRegistered(email)

    user = User(
        email=email,
        password_hash=hash_password(password),
        auth_provider="local",
        name=name,
        journal_theme=journal_theme,
    )
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(email_raw: str, password: str) -> User | None:
    email = domain.canonical_email(email_raw)
    user = db.session.query(User).filter(User.email == email).one_or_none()
    if user is None or user.auth_provider != "local":
        verify_password(None, password)
        return None
    if not verify_password(user.password_hash, password):
        return None
    return user


def token_secret_strength() -> bool:
    return len(current_app.config["JWT_SECRET_KEY"]) >= 32


__all__ = [
    "COOKIE_NAME",
    "authenticate",
    "clear_session_cookie",
    "current_user",
    "decode_token",
    "hash_password",
    "issue_token",
    "register_user",
    "set_session_cookie",
    "token_secret_strength",
    "verify_password",
]
