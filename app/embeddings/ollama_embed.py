from typing import List
import ollama
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("ollama_embed")

class OllamaEmbeddingClient:
    """
    Client kết nối tới Ollama phục vụ cho việc tạo Vector Embedding cho văn bản.
    """
    def __init__(self):
        self.client = ollama.Client(host=settings.OLLAMA_BASE_URL)
        self.model = settings.OLLAMA_EMBED_MODEL

    def get_embedding(self, text: str) -> List[float]:
        """
        Tạo vector embedding cho một chuỗi văn bản đơn lẻ.
        """
        try:
            # Làm sạch chuỗi trước khi gửi
            cleaned_text = text.strip().replace("\n", " ")
            response = self.client.embeddings(
                model=self.model,
                prompt=cleaned_text
            )
            embedding = response.get("embedding")
            if not embedding:
                raise ValueError("Ollama API trả về response không chứa trường 'embedding'.")
            return embedding
        except Exception as e:
            logger.error(f"Lỗi sinh embedding với model '{self.model}': {e}")
            raise RuntimeError(f"Lỗi kết nối hoặc sinh embedding từ Ollama: {str(e)}")

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Tạo vector embedding cho danh sách các chuỗi văn bản.
        """
        logger.info(f"Đang sinh vector embedding cho {len(texts)} đoạn văn bản...")
        results = []
        for i, text in enumerate(texts):
            emb = self.get_embedding(text)
            results.append(emb)
        return results
