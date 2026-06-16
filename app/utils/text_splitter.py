from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings

def split_text(text: str) -> List[str]:
    """
    Chia nhỏ văn bản thành các đoạn (chunks) có kích thước vừa phải và chồng lấp ngữ cảnh.
    Sử dụng tham số CHUNK_SIZE và CHUNK_OVERLAP từ cấu hình ứng dụng.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)
