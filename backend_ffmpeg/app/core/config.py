import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Конфигурация S3 (MinIO)
class Settings:
    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://192.168.1.17:9000")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "videos")

settings = Settings()
