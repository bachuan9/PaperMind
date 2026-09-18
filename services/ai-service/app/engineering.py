import logging
from collections import defaultdict, deque
from time import monotonic, perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .settings import Settings


logger = logging.getLogger("papermind.api")


class RequestLogAndLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, settings: Settings):
        super().__init__(app)
        self.settings = settings
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        started = perf_counter()

        limited_response = self._rate_limit(request, request_id)
        if limited_response is not None:
            return limited_response

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        if self.settings.ai_request_log_enabled:
            duration_ms = int((perf_counter() - started) * 1000)
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
        return response

    def _rate_limit(self, request: Request, request_id: str) -> JSONResponse | None:
        limit = self.settings.ai_rate_limit_per_minute
        if limit <= 0 or request.url.path == "/health":
            return None

        client_host = request.client.host if request.client else "unknown"
        now = monotonic()
        bucket = self._requests[client_host]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(60 - (now - bucket[0])))
            response = error_response(
                status_code=429,
                code="rate_limited",
                message="请求过于频繁，请稍后再试",
                request_id=request_id,
            )
            response.headers["retry-after"] = str(retry_after)
            return response

        bucket.append(now)
        return None


def configure_engineering(app: FastAPI, settings: Settings) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.add_middleware(RequestLogAndLimitMiddleware, settings=settings)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = get_request_id(request)
        return error_response(
            status_code=exc.status_code,
            code=http_code(exc.status_code),
            message=str(exc.detail),
            request_id=request_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = get_request_id(request)
        return error_response(
            status_code=422,
            code="validation_error",
            message="请求参数格式不正确",
            request_id=request_id,
            errors=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = get_request_id(request)
        logger.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        return error_response(
            status_code=500,
            code="internal_error",
            message="服务暂时不可用，请稍后再试",
            request_id=request_id,
        )


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    errors: list | None = None,
) -> JSONResponse:
    payload = {
        "detail": message,
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        },
    }
    if errors is not None:
        payload["error"]["errors"] = errors
    response = JSONResponse(status_code=status_code, content=payload)
    response.headers["x-request-id"] = request_id
    return response


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def http_code(status_code: int) -> str:
    return {
        400: "bad_request",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        422: "validation_error",
        429: "rate_limited",
    }.get(status_code, "http_error")
