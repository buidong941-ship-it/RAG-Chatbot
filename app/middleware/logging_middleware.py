import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.utils.logger import get_logger

logger = get_logger("middleware.request_logging")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware tự động ghi log mọi HTTP request và response.

    Thông tin được ghi log:
    - Địa chỉ IP của client
    - HTTP Method (GET, POST, ...)
    - URL path và query string
    - Status code của response
    - Thời gian xử lý request (milliseconds)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # --- Ghi nhận thông tin request đầu vào ---
        start_time = time.perf_counter()

        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query = request.url.query

        full_path = f"{path}?{query}" if query else path

        logger.info(
            f"➡️  [{method}] {full_path} — IP: {client_ip}"
        )

        # --- Chuyển xử lý cho endpoint tiếp theo ---
        response: Response = await call_next(request)

        # --- Ghi nhận thông tin sau khi response hoàn tất ---
        process_time_ms = (time.perf_counter() - start_time) * 1000
        status_code = response.status_code

        # Thêm header X-Process-Time vào response để client có thể kiểm tra
        response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"

        log_level = logger.info
        if status_code >= 500:
            log_level = logger.error
        elif status_code >= 400:
            log_level = logger.warning

        log_level(
            f"⬅️  [{method}] {full_path} → {status_code} ({process_time_ms:.2f}ms)"
        )

        return response
