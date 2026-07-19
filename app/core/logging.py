import json
import logging
import time
import uuid
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.modules.auth.security import decode_token

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def _handler(path: str, formatter: logging.Formatter) -> RotatingFileHandler:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        file_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    return handler


def configure_logging() -> None:
    """Настраивает технический и аудит-лог в отдельных файлах."""
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())
    root.addHandler(_handler(settings.log_file, formatter))

    audit_logger = logging.getLogger("audit")
    audit_logger.handlers.clear()
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    audit_logger.addHandler(_handler(settings.audit_log_file, formatter))

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.log_sql else logging.WARNING
    )


def audit_event(
    action: str,
    *,
    actor_id: int | None = None,
    entity: str | None = None,
    entity_id: int | str | None = None,
    branch_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Записывает структурированное событие аудита без чувствительных данных."""
    payload = {
        "action": action,
        "actor_id": actor_id,
        "entity": entity,
        "entity_id": entity_id,
        "branch_id": branch_id,
        "details": details or {},
    }
    logging.getLogger("audit").info(json.dumps(payload, ensure_ascii=False, default=str))


def _actor_id(request: Request) -> int | None:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
        if payload.get("type") != "access":
            return None
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None


def _audit_action(request: Request) -> tuple[str, str | None] | None:
    method = request.method
    path = request.url.path

    if method == "POST" and path.endswith("/auth/login"):
        return "auth.login", "auth"
    if method == "POST" and path.endswith("/auth/change-password"):
        return "auth.password_changed", "user"

    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None

    parts = [part for part in path.split("/") if part]
    if "v1" in parts:
        parts = parts[parts.index("v1") + 1 :]
    if not parts:
        return None

    entity = parts[0]
    suffix = ".deleted" if method == "DELETE" else {
        "POST": ".created_or_action",
        "PUT": ".synchronized",
        "PATCH": ".updated",
    }[method]
    return entity + suffix, entity


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Логирует все запросы и успешные изменяющие действия пользователей."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        logger = logging.getLogger("http")

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "method=%s path=%s status=%s duration_ms=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

            event = _audit_action(request)
            if event and response.status_code < 400:
                action, entity = event
                path_params = request.scope.get("path_params", {})
                entity_id = next(
                    (value for key, value in path_params.items() if key.endswith("_id")),
                    None,
                )
                audit_event(
                    action,
                    actor_id=_actor_id(request),
                    entity=entity,
                    entity_id=entity_id,
                    details={"method": request.method, "path": request.url.path},
                )

            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            logger.exception("method=%s path=%s unhandled_error", request.method, request.url.path)
            raise
        finally:
            request_id_ctx.reset(token)
