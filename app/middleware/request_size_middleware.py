from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger("middleware.request_size")


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware giới hạn kích thước body của HTTP request.

    - Giới hạn được lấy từ cấu hình `settings.MAX_UPLOAD_SIZE_MB` (mặc định 20 MB).
    - Nếu request vượt quá giới hạn → trả về HTTP 413 Request Entity Too Large.
    - Chỉ áp dụng cho các request có header Content-Length.
      (Các request không có header này vẫn được pass-through bình thường.)
    """

    def __init__(self, app):
        super().__init__(app)
        # Chuyển đổi MB → Bytes
        self.max_size_bytes: int = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")

        if content_length is not None:
            try:
                body_size = int(content_length)
            except ValueError:
                logger.warning(
                    f"Header Content-Length không hợp lệ: '{content_length}' "
                    f"từ IP {request.client.host if request.client else 'unknown'}"
                )
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Header Content-Length không hợp lệ."},
                )

            if body_size > self.max_size_bytes:
                max_mb = settings.MAX_UPLOAD_SIZE_MB
                actual_mb = round(body_size / (1024 * 1024), 2)
                logger.warning(
                    f"Request bị từ chối: kích thước {actual_mb} MB "
                    f"vượt quá giới hạn {max_mb} MB — "
                    f"path={request.url.path}, "
                    f"IP={request.client.host if request.client else 'unknown'}"
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": (
                            f"Kích thước file ({actual_mb} MB) vượt quá giới hạn tối đa cho phép "
                            f"({max_mb} MB). Vui lòng nén hoặc chia nhỏ tài liệu trước khi tải lên."
                        )
                    },
                )

        return await call_next(request)
