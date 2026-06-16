import ollama
from sqlalchemy.orm import Session
from app.models.models import Chunk, ChatHistory
from app.embeddings.ollama_embed import OllamaEmbeddingClient
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("rag_service")

class RAGService:
    """
    Dịch vụ xử lý luồng RAG (Retrieval-Augmented Generation):
    1. Nhận câu hỏi và chuyển câu hỏi thành Vector Embedding.
    2. Tìm kiếm các chunks văn bản tương đồng nhất trong database (similarity search sử dụng cosine distance).
    3. Ghép các chunks làm ngữ cảnh (context) để đưa vào prompt cho LLM.
    4. Gọi LLM của Ollama để sinh ra câu trả lời cuối cùng.
    5. Lưu vết câu hỏi, câu trả lời vào lịch sử trò chuyện.
    """
    def __init__(self):
        self.embed_client = OllamaEmbeddingClient()
        self.ollama_client = ollama.Client(host=settings.OLLAMA_BASE_URL)
        self.llm_model = settings.OLLAMA_LLM_MODEL

    def search_similar_chunks(self, db: Session, query_text: str, top_k: int = None) -> list[Chunk]:
        """
        Tìm kiếm các đoạn văn bản tương đồng nhất trong database bằng pgvector.
        """
        if top_k is None:
            top_k = settings.TOP_K

        # Tạo embedding cho câu hỏi
        query_embedding = self.embed_client.get_embedding(query_text)

        # Sử dụng cosine_distance (<=>) để tìm kiếm tương đồng
        # Khoảng cách cosine càng nhỏ, độ tương đồng càng cao
        chunks = db.query(Chunk).order_by(
            Chunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k).all()

        return chunks

    def generate_answer(self, db: Session, question: str) -> dict:
        """
        Thực hiện toàn bộ quy trình RAG và lưu vào lịch sử chat.
        """
        try:
            # 1. Tìm các chunk tương đồng nhất
            chunks = self.search_similar_chunks(db, question)
            
            # 2. Xây dựng ngữ cảnh từ các chunk tìm thấy
            if not chunks:
                context_str = "Không tìm thấy thông tin phù hợp trong kho tài liệu."
                logger.warning(f"Không có chunks tương đồng nào được tìm thấy cho câu hỏi: '{question}'")
            else:
                context_str = "\n\n".join([
                    f"[Tài liệu: {chunk.document.filename}]\n{chunk.content}"
                    for chunk in chunks
                ])

            # 3. Tạo prompt gửi tới LLM
            prompt = (
                "Bạn là một trợ lý AI tiếng Việt thông minh và thân thiện. Hãy trả lời câu hỏi của người dùng một cách trung thực "
                "và chi tiết dựa vào ngữ cảnh tài liệu được cung cấp dưới đây. Nếu ngữ cảnh không có thông tin phù hợp, hãy dùng kiến thức "
                "của bạn để giải thích hoặc trả lời, nhưng cần nêu rõ là thông tin này không nằm trong tài liệu tải lên.\n\n"
                f"=== NGỮ CẢNH TÀI LIỆU ===\n{context_str}\n=========================\n\n"
                f"Câu hỏi: {question}\n\n"
                "Trả lời:"
            )

            # 4. Gửi yêu cầu sinh văn bản tới Ollama LLM
            logger.info(f"Đang sinh câu trả lời bằng model '{self.llm_model}'...")
            response = self.ollama_client.generate(
                model=self.llm_model,
                prompt=prompt,
                options={
                    "temperature": 0.2,  # Giảm độ ngẫu nhiên để tăng tính chính xác
                    "top_p": 0.9
                }
            )
            answer = response.get("response", "").strip()

            # 5. Lưu kết quả hội thoại vào DB
            chat_record = ChatHistory(
                question=question,
                answer=answer
            )
            db.add(chat_record)
            db.commit()
            db.refresh(chat_record)

            return {
                "question": question,
                "answer": answer,
                "sources": [
                    {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "filename": chunk.document.filename,
                        "content": chunk.content
                    }
                    for chunk in chunks
                ],
                "created_at": chat_record.created_at
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Lỗi trong quá trình xử lý sinh câu trả lời RAG: {e}")
            raise RuntimeError(f"Lỗi xử lý RAG: {str(e)}")
