from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# Sử dụng engine đồng bộ cho SQLAlchemy 2.0
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Tự động kiểm tra trạng thái kết nối trước khi dùng
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# Dependency cung cấp database session cho FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
