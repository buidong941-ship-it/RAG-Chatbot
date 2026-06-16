import logging
import sys

# Cấu hình định dạng log
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Hàm lấy logger
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
