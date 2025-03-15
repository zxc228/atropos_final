import boto3
from botocore.exceptions import NoCredentialsError
from app.core.config import settings
from fastapi.responses import FileResponse
from fastapi import HTTPException
import os

# Создание клиента MinIO (boto3)
s3 = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY
)

# Функция загрузки видео
def upload_video(file, filename):
    try:
        s3.upload_fileobj(file, settings.S3_BUCKET_NAME, filename)
        return f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET_NAME}/{filename}"
    except NoCredentialsError:
        return None

# Функция получения URL видео
def get_video_url(video_id):
    return f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET_NAME}/{video_id}"

# Функция получения списка видео
def list_videos():
    try:
        response = s3.list_objects_v2(Bucket=settings.S3_BUCKET_NAME)

        if "Contents" not in response:
            return []

        return [
            {
                "Key": obj["Key"],
                "LastModified": obj["LastModified"].isoformat(),  # ✅ Конвертируем datetime в строку
                "Size": obj["Size"]
            }
            for obj in response["Contents"]
        ]

    except Exception as e:
        return []

# Функция удаления видео
def delete_video(video_id):
    s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=video_id)

# ✅ Функция скачивания видео из S3 и передачи пользователю
def download_video(video_id):
    local_file = f"/tmp/{video_id}"  # Временное хранилище файла

    try:
        # Загружаем файл из S3 в локальное хранилище
        s3.download_file(settings.S3_BUCKET_NAME, video_id, local_file)

        # Проверяем, существует ли скачанный файл
        if not os.path.exists(local_file):
            raise FileNotFoundError(f"Файл {video_id} не найден после загрузки!")

        # Отправляем файл пользователю
        return FileResponse(local_file, media_type="video/mp4", filename=video_id)
    
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="Ошибка доступа к S3")
    
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ошибка загрузки: {str(e)}")
