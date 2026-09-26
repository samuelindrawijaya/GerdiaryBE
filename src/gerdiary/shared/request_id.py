from __future__ import annotations

from uuid import UUID, uuid4

from flask import Flask, Response, g, request


def _resolve_request_id(value: str | None) -> str:
    if value is None:
        return str(uuid4())
    try:
        return str(UUID(value))
    except ValueError:
        return str(uuid4())


def current_request_id() -> str:
    return str(g.get("request_id", ""))


def register_request_id(app: Flask) -> None:
    @app.before_request
    def assign_request_id() -> None:
        g.request_id = _resolve_request_id(request.headers.get("X-Request-ID"))

    @app.after_request
    def add_request_id(response: Response) -> Response:
        response.headers["X-Request-ID"] = current_request_id()
        return response


__all__: list[str] = ["register_request_id", "current_request_id"]
