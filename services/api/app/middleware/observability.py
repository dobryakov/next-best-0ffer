from __future__ import annotations

import logging
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

TRACE_HEADER = "X-Trace-Id"
CORRELATION_HEADER = "X-Correlation-Id"
REQUEST_HEADER = "X-Request-Id"


def _resolve_log_level(level: str) -> int:
    try:
        return getattr(logging, level.upper())
    except AttributeError:
        return logging.INFO


def configure_structlog(level: str = "INFO") -> None:
    """Настройка структурированного логирования и контекстов request/trace."""

    logging.basicConfig(
        format="%(message)s",
        level=_resolve_log_level(level),
    )

    structlog.configure(
        cache_logger_on_first_use=True,
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            structlog.processors.EventRenamer("event"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def _generate_request_id() -> str:
    return uuid.uuid4().hex


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware добавляет trace-id, correlation-id и логирует HTTP запросы."""

    def __init__(self, app, service_name: str, logger: structlog.BoundLogger | None = None) -> None:
        super().__init__(app)
        self._service_name = service_name
        self._logger = logger or structlog.get_logger(service_name)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        incoming_trace = request.headers.get(TRACE_HEADER)
        trace_id = incoming_trace or _generate_request_id()
        correlation_id = request.headers.get(CORRELATION_HEADER) or trace_id
        request_id = request.headers.get(REQUEST_HEADER) or trace_id

        bindings = {
            "trace_id": trace_id,
            "correlation_id": correlation_id,
            "request_id": request_id,
            "service": self._service_name,
            "method": request.method,
            "path": request.url.path,
        }

        start = time.perf_counter()

        with structlog.contextvars.bound_contextvars(**bindings):
            request.state.trace_id = trace_id
            request.state.correlation_id = correlation_id
            request.state.request_id = request_id
            request.state.logger = self._logger.bind(**bindings)

            try:
                response = await call_next(request)
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                request.state.logger.exception(
                    "http.request.error",
                    duration_ms=duration_ms,
                    error_type=type(exc).__name__,
                )
                raise

            duration_ms = (time.perf_counter() - start) * 1000
            response.headers.setdefault(TRACE_HEADER, trace_id)
            response.headers.setdefault(CORRELATION_HEADER, correlation_id)
            response.headers.setdefault(REQUEST_HEADER, request_id)

            request.state.logger.info(
                "http.request.completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            return response


