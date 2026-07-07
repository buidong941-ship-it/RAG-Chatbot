from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from app.database.session import engine, SessionLocal, Base
from app.api.endpoints import router as api_router
from app.middleware import RequestLoggingMiddleware, RequestSizeLimitMiddleware
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Quản lý vòng đời (lifespan) của ứng dụng FastAPI.
    Tự động chạy các đoạn mã khởi tạo (startup) và dọn dẹp (shutdown).
    """
    logger.info("Khởi động hệ thống RAG Chatbot...")

    # Khởi tạo database, tạo extension và tạo bảng
    try:
        logger.info("Đang kiểm tra và tạo extension 'vector' trong PostgreSQL...")
        with SessionLocal() as db:
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            db.commit()
            logger.info("Đã xác nhận hoặc cài đặt thành công pgvector extension.")

        logger.info("Đang đồng bộ hóa cấu trúc bảng với SQLAlchemy metadata...")
        # Import models để SQLAlchemy nhận diện các table trước khi tạo
        from app.models import models
        Base.metadata.create_all(bind=engine)
        logger.info("Đã khởi tạo và đồng bộ hóa các bảng thành công.")
    except Exception as e:
        logger.critical(f"Lỗi nghiêm trọng khi khởi tạo cơ sở dữ liệu: {e}")
        # Không chặn tiến trình startup nhưng log cảnh báo sâu sắc
        # Trong môi trường Docker hoặc production, có thể db chưa sẵn sàng, nên bắt lỗi ở đây

    yield

    logger.info("Đang tắt hệ thống RAG Chatbot...")

app = FastAPI(
    title="Local RAG Chatbot API",
    description="Hệ thống Chatbot RAG hoàn chỉnh chạy trên môi trường cục bộ (Local) sử dụng Ollama và PostgreSQL pgvector.",
    version="1.0.0",
    lifespan=lifespan
)

# =============================================================================
# ĐĂNG KÝ MIDDLEWARE
# Lưu ý: FastAPI/Starlette xử lý middleware theo thứ tự LIFO (vào sau - ra trước).
# Middleware đăng ký cuối cùng sẽ là lớp bao ngoài cùng, xử lý request đầu tiên.
#
# Luồng request thực tế (từ ngoài vào trong):
#   Client → [4] RequestLoggingMiddleware
#           → [3] RequestSizeLimitMiddleware
#           → [2] GZipMiddleware
#           → [1] CORSMiddleware
#           → Router / Endpoints
# =============================================================================

# [1] CORSMiddleware — Xử lý CORS headers (đăng ký đầu tiên = lớp trong cùng)
# Phân tích ALLOWED_ORIGINS từ cấu hình: "*" hoặc danh sách cách nhau bởi dấu phẩy
_raw_origins = settings.ALLOWED_ORIGINS.strip()
allowed_origins: list[str] = (
    ["*"] if _raw_origins == "*"
    else [o.strip() for o in _raw_origins.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False if "*" in allowed_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [2] GZipMiddleware — Nén response body (giảm băng thông)
# minimum_size=1000: chỉ nén nếu response > 1000 bytes
app.add_middleware(GZipMiddleware, minimum_size=1000)

# [3] RequestSizeLimitMiddleware — Giới hạn kích thước upload (đọc từ config)
app.add_middleware(RequestSizeLimitMiddleware)

# [4] RequestLoggingMiddleware — Log request/response (đăng ký cuối = lớp ngoài cùng)
app.add_middleware(RequestLoggingMiddleware)

# =============================================================================

# Đăng ký API router
app.include_router(api_router)

# Mount thư mục static phục vụ file giao diện
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", tags=["Root"])
def root():
    return FileResponse("static/index.html")

