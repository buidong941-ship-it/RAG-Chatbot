import os
import shutil
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Document, Chunk, ChatHistory
from app.services.document_parser import DocumentParser
from app.utils.text_splitter import split_text
from app.embeddings.ollama_embed import OllamaEmbeddingClient
from app.rag.rag_service import RAGService
from app.utils.logger import get_logger

logger = get_logger("api_endpoints")

router = APIRouter(prefix="/api")

# --- Thư mục lưu file upload ---
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Pydantic Schemas ---
class QueryRequest(BaseModel):
    question: str

class SourceSchema(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    content: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceSchema]
    created_at: datetime

class DocumentResponse(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class ChatHistoryResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- API Endpoints ---

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Tải lên file tài liệu (PDF, DOCX, TXT), phân tích nội dung, chia nhỏ thành chunks,
    sinh embeddings qua Ollama và lưu trữ vào PostgreSQL vector DB.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    # 1. Kiểm tra định dạng file
    if ext not in [".pdf", ".docx", ".doc", ".txt"]:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng file {ext} không được hỗ trợ. Chỉ nhận file PDF, DOCX, TXT."
        )
    
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    try:
        # 2. Lưu file vào thư mục upload
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Đã lưu file thành công tại: {file_path}")

        # 3. Phân tích nội dung file văn bản
        text_content = DocumentParser.parse(file_path)
        if not text_content.strip():
            # Xóa file lỗi
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail="Tài liệu tải lên không có nội dung văn bản để phân tích."
            )
        
        # 4. Lưu metadata của tài liệu vào DB
        db_doc = Document(filename=filename)
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)

        # 5. Chia nhỏ văn bản thành các chunks
        chunks = split_text(text_content)
        logger.info(f"Tài liệu '{filename}' được phân tách thành {len(chunks)} chunks.")

        if not chunks:
            # Nếu không chia nhỏ được chunk nào, xóa thông tin doc
            db.delete(db_doc)
            db.commit()
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail="Không thể phân nhỏ tài liệu này thành các đoạn văn bản hợp lệ."
            )

        # 6. Tạo vector embedding cho các chunks
        embed_client = OllamaEmbeddingClient()
        chunk_embeddings = embed_client.get_embeddings(chunks)

        # 7. Lưu các chunks kèm vector embedding tương ứng
        db_chunks = []
        for content, embedding in zip(chunks, chunk_embeddings):
            db_chunk = Chunk(
                document_id=db_doc.id,
                content=content,
                embedding=embedding
            )
            db_chunks.append(db_chunk)
        
        db.bulk_save_objects(db_chunks)
        db.commit()
        logger.info(f"Đã lưu thành công {len(db_chunks)} chunks vào Database cho file '{filename}'.")

        return db_doc

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Lỗi xảy ra trong quá trình tải lên và xử lý file '{filename}': {e}")
        db.rollback()
        # Dọn dẹp file lưu lỗi
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi hệ thống khi xử lý tài liệu: {str(e)}"
        )


@router.post("/query", response_model=QueryResponse)
def query_rag(request: QueryRequest, db: Session = Depends(get_db)):
    """
    API tiếp nhận câu hỏi của người dùng, thực hiện tìm kiếm tương đồng trên pgvector DB,
    xây dựng ngữ cảnh phù hợp, gửi yêu cầu tới Ollama LLM và trả về câu trả lời hoàn chỉnh kèm nguồn trích dẫn.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")
    
    try:
        rag_service = RAGService()
        result = rag_service.generate_answer(db, question)
        return result
    except Exception as e:
        logger.error(f"Lỗi truy vấn RAG cho câu hỏi '{question}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xử lý câu hỏi RAG: {str(e)}"
        )


@router.get("/documents", response_model=List[DocumentResponse])
def get_all_documents(db: Session = Depends(get_db)):
    """
    Lấy danh sách thông tin các tài liệu đã được tải lên và lưu trong database.
    """
    try:
        documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()
        return documents
    except Exception as e:
        logger.error(f"Lỗi lấy danh sách tài liệu: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi truy vấn cơ sở dữ liệu: {str(e)}"
        )


@router.get("/chat-history", response_model=List[ChatHistoryResponse])
def get_chat_history(db: Session = Depends(get_db)):
    """
    Lấy toàn bộ lịch sử hỏi đáp của người dùng với hệ thống RAG chatbot.
    """
    try:
        history = db.query(ChatHistory).order_by(ChatHistory.created_at.desc()).all()
        return history
    except Exception as e:
        logger.error(f"Lỗi lấy lịch sử trò chuyện: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi truy vấn lịch sử trò chuyện: {str(e)}"
        )
