import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5433/ragdb"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIM: int = 768
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 4

    # --- Middleware Settings ---
    # Kích thước tối đa của file được phép upload (MB)
    MAX_UPLOAD_SIZE_MB: int = 20
    # Danh sách origins được phép gọi API (dùng "*" để cho phép tất cả, hoặc
    # nhập danh sách cách nhau bởi dấu phẩy: "http://localhost:3000,https://myapp.com")
    ALLOWED_ORIGINS: str = "*"

settings = Settings()
