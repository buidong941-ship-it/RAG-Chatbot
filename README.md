# RAG Chatbot

Ứng dụng chatbot RAG chạy local/offline với FastAPI, Ollama, PostgreSQL và pgvector. Người dùng có thể upload tài liệu PDF/DOCX/TXT, hệ thống sẽ chia nhỏ nội dung, tạo embedding, lưu vào vector database và dùng LLM local để trả lời câu hỏi dựa trên tài liệu.

## Tính Năng

- Giao diện web để upload tài liệu và chat.
- Backend FastAPI phục vụ cả API và static web UI.
- Ollama dùng cho LLM và embedding model.
- PostgreSQL + pgvector dùng làm vector database.
- Lưu lịch sử chat và danh sách tài liệu đã upload.
- Chạy local, không cần gửi dữ liệu tài liệu lên dịch vụ cloud.

## Kiến Trúc

```text
Browser
  |
  v
FastAPI app
  |
  |-- PostgreSQL + pgvector: lưu documents, chunks, embeddings, chat_history
  |
  |-- Ollama: tạo embedding và sinh câu trả lời
```

## Cấu Trúc Dự Án

```text
CHAT_BOT/
  app/
    api/endpoints.py          API upload, query, documents, chat-history
    database/session.py       Kết nối database
    embeddings/ollama_embed.py
    models/models.py          SQLAlchemy models
    rag/rag_service.py        Luồng RAG chính
    services/document_parser.py
    utils/logger.py
    utils/text_splitter.py
    config.py                 Đọc cấu hình từ .env
  static/
    index.html
    index.css
    index.js
  uploads/                    File người dùng upload, không nên push lên GitHub
  docker-compose.yml          PostgreSQL + Ollama
  requirements.txt
  main.py
  .env.example                File mẫu cấu hình môi trường
  .gitignore                  Danh sách file không nên push
  README.md
```

## Yêu Cầu

- Docker Desktop
- Python 3.10 trở lên
- Git
- RAM tối thiểu 8GB nếu dùng model nhỏ
- GPU NVIDIA là tùy chọn, không bắt buộc

## Cài Docker Desktop

### Windows

1. Tải Docker Desktop tại trang chính thức: `https://www.docker.com/products/docker-desktop/`
2. Cài đặt Docker Desktop.
3. Bật WSL2 nếu Docker yêu cầu.
4. Mở Docker Desktop và chờ trạng thái `Docker Desktop is running`.
5. Kiểm tra:

```powershell
docker --version
docker compose version
```

### macOS / Linux

Cài Docker theo hướng dẫn chính thức của Docker cho hệ điều hành của bạn, sau đó kiểm tra:

```bash
docker --version
docker compose version
```

## Clone Và Cài Đặt

```bash
git clone <repo-url>
cd CHAT_BOT
```

Tạo file `.env` từ file mẫu:

```bash
cp .env.example .env
```

Trên Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

## Chọn Port PostgreSQL

Container PostgreSQL bên trong luôn chạy port `5432`. Phần cần chọn là port trên máy host.

### Trường Hợp 1: Máy Chưa Có PostgreSQL

Bạn có thể dùng port mặc định `5432`.

Trong `docker-compose.yml`:

```yaml
ports:
  - "5432:5432"
```

Trong `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ragdb
```

### Trường Hợp 2: Máy Đã Có PostgreSQL Chạy Ở Port 5432

Dùng port `5433` để tránh xung đột.

Trong `docker-compose.yml`:

```yaml
ports:
  - "5433:5432"
```

Trong `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ragdb
```

Project hiện tại của bạn đang dùng lựa chọn `5433`.

## Chạy Docker Services

Khởi động PostgreSQL + Ollama:

```bash
docker compose up -d
```

Kiểm tra container:

```bash
docker ps
```

Bạn nên thấy 2 container:

```text
pgvector
ollama
```

## Tải Model Vào Ollama

Embedding model bắt buộc:

```bash
docker exec ollama ollama pull nomic-embed-text
```

LLM khuyến nghị cho máy phổ thông:

```bash
docker exec ollama ollama pull qwen2.5:3b
```

Nếu máy mạnh hơn, có thể dùng Llama:

```bash
docker exec ollama ollama pull llama3.1:8b
```

Kiểm tra model đã tải:

```bash
docker exec ollama ollama list
```

## Gợi Ý Chọn Model Theo Cấu Hình Máy

Các con số dưới đây là kinh nghiệm thực tế tương đối, còn tốc độ phụ thuộc CPU, RAM, VRAM, quantization và độ dài prompt.

| Model | Phù hợp với | RAM nên có | GPU/VRAM gợi ý | Ghi chú |
|---|---:|---:|---:|---|
| `qwen2.5:1.5b` | Máy yếu, test nhanh | 8GB | Không bắt buộc, 2GB VRAM có thể thử | Nhanh hơn, chất lượng vừa đủ |
| `qwen2.5:3b` | Máy phổ thông | 8GB - 16GB | 4GB VRAM trở lên tốt hơn | Cân bằng tốc độ và chất lượng |
| `llama3.2:3b` | Máy phổ thông | 8GB - 16GB | 4GB VRAM trở lên | Có thể thay thế Qwen 3B |
| `llama3.1:8b` | Máy mạnh | 16GB - 32GB | 8GB VRAM trở lên | Trả lời tốt hơn nhưng chậm/nặng hơn |
| `mistral:7b` | Máy khá mạnh | 16GB - 32GB | 8GB VRAM trở lên | Khá ổn cho nhiều tác vụ |

Nếu `docker exec ollama ollama ps` hiển thị `100% CPU`, model đang chạy bằng CPU. Khi đó câu trả lời sẽ chậm hơn nhiều so với GPU.

Kiểm tra model đang chạy bằng CPU hay GPU:

```bash
docker exec ollama ollama ps
```

Ví dụ đang chạy CPU:

```text
NAME          PROCESSOR
qwen2.5:3b    100% CPU
```

## Cấu Hình `.env`

Ví dụ cho máy đang dùng PostgreSQL host port `5433`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ragdb
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=qwen2.5:3b
OLLAMA_EMBED_MODEL=nomic-embed-text
EMBEDDING_DIM=768
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=4
```

Ý nghĩa:

| Biến | Ý nghĩa |
|---|---|
| `DATABASE_URL` | Chuỗi kết nối PostgreSQL |
| `OLLAMA_BASE_URL` | URL Ollama local |
| `OLLAMA_LLM_MODEL` | Model sinh câu trả lời |
| `OLLAMA_EMBED_MODEL` | Model tạo embedding |
| `EMBEDDING_DIM` | Số chiều embedding, `nomic-embed-text` dùng 768 |
| `CHUNK_SIZE` | Kích thước mỗi đoạn văn bản |
| `CHUNK_OVERLAP` | Số ký tự chồng lấp giữa các đoạn |
| `TOP_K` | Số đoạn tài liệu liên quan được đưa vào prompt |

Nếu trả lời quá chậm, thử giảm:

```env
CHUNK_SIZE=300
TOP_K=2
```

Sau khi đổi `.env`, hãy restart FastAPI.

## Cài Python Dependencies

Tạo môi trường ảo:

```bash
python -m venv venv
```

Kích hoạt môi trường ảo.

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
venv\Scripts\activate.bat
```

macOS / Linux:

```bash
source venv/bin/activate
```

Cài dependencies:

```bash
pip install -r requirements.txt
```

## Chạy Ứng Dụng

Đảm bảo Docker services đã chạy:

```bash
docker compose up -d
```

Chạy FastAPI:

```bash
uvicorn main:app --reload
```

Mở trình duyệt:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Sử Dụng Từ Đầu Đến Cuối

1. Mở `http://127.0.0.1:8000`.
2. Kéo thả file PDF/DOCX/TXT vào khu vực upload bên trái.
3. Chờ hệ thống upload, đọc nội dung, chia chunk và tạo embedding.
4. Nhập câu hỏi ở ô chat.
5. Nhấn Enter để gửi.
6. Backend tìm các đoạn tài liệu liên quan trong pgvector.
7. Backend gửi context + câu hỏi sang Ollama.
8. Ollama sinh câu trả lời.
9. Giao diện hiển thị câu trả lời kèm nguồn trích dẫn.

Log quan trọng khi generate:

```text
rag_service - INFO - Đang sinh câu trả lời bằng model 'qwen2.5:3b'
```

Dòng này nằm trong `app/rag/rag_service.py`, ngay trước lúc gọi Ollama để sinh câu trả lời.

## API Nhanh Bằng Curl

Upload tài liệu:

```bash
curl -X POST "http://127.0.0.1:8000/api/upload" \
  -H "accept: application/json" \
  -F "file=@/path/to/document.pdf"
```

Đặt câu hỏi:

```bash
curl -X POST "http://127.0.0.1:8000/api/query" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"Tài liệu này nói về gì?\"}"
```

Lấy danh sách tài liệu:

```bash
curl "http://127.0.0.1:8000/api/documents"
```

Lấy lịch sử chat:

```bash
curl "http://127.0.0.1:8000/api/chat-history"
```

## GPU NVIDIA

Trong `docker-compose.yml`, đoạn này yêu cầu Docker cấp GPU NVIDIA cho container Ollama:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

Đoạn này không đảm bảo chắc chắn model dùng GPU. Nó chỉ có tác dụng khi máy đã có NVIDIA driver, Docker/WSL2 hỗ trợ GPU và GPU đủ VRAM.

Kiểm tra trên Windows host:

```powershell
nvidia-smi
```

Kiểm tra model Ollama đang chạy bằng gì:

```bash
docker exec ollama ollama ps
```

Nếu vẫn là `100% CPU`, app vẫn chạy được nhưng tốc độ generate sẽ chậm.

## Restart

Nếu đổi `.env`, dừng FastAPI bằng `Ctrl + C`, sau đó chạy lại:

```bash
uvicorn main:app --reload
```

Nếu đổi `docker-compose.yml`, restart Docker services:

```bash
docker compose down
docker compose up -d
```

## Lệnh Docker Hữu Ích

```bash
# Khởi động services
docker compose up -d

# Dừng services, giữ dữ liệu volume
docker compose down

# Dừng và xóa dữ liệu database/model trong volume
docker compose down -v

# Xem log Ollama
docker logs -f ollama

# Xem log PostgreSQL
docker logs -f pgvector

# Danh sách model Ollama
docker exec ollama ollama list

# Model đang chạy
docker exec ollama ollama ps

# Vào PostgreSQL
docker exec -it pgvector psql -U postgres -d ragdb
```

```

## Lỗi Thường Gặp

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| Không kết nối được database | Docker chưa chạy hoặc sai port | Chạy `docker compose up -d`, kiểm tra `DATABASE_URL` |
| Port 5432 bị chiếm | Máy đã có PostgreSQL local | Đổi compose sang `5433:5432` và `.env` sang port `5433` |
| Model not found | Chưa pull model | Chạy `docker exec ollama ollama pull <model>` |
| Generate lâu | Model chạy CPU, prompt dài, model lớn | Dùng model nhỏ hơn, giảm `TOP_K`, giảm `CHUNK_SIZE` |
| Upload lỗi | File không đúng định dạng | Dùng PDF, DOCX, DOC hoặc TXT |
| UI hiện sai tên model | Tên trong HTML đang hard-code | Sửa `static/index.html` hoặc thêm API trả config |
