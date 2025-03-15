from fastapi import APIRouter, File, UploadFile, HTTPException
from app.core.services.s3 import upload_video, get_video_url, list_videos, delete_video, download_video
from fastapi.responses import FileResponse
import os
import uuid

router = APIRouter()

# 1️⃣ Загрузка видео
@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    url = upload_video(file.file, unique_filename)
    if not url:
        raise HTTPException(status_code=500, detail="Ошибка загрузки в S3")
    return {"message": "Видео загружено", "url": url}

# 2️⃣ Получение списка видео (СТАТИЧЕСКИЙ РОУТ ДОЛЖЕН ИДТИ ПЕРВЫМ!)
@router.get("/list")
async def get_list():
    files = list_videos()
    return files

@router.get("/download/{video_id}")
async def download(video_id: str):
    return download_video(video_id)


# 3️⃣ Получение ссылки на видео (ДИНАМИЧЕСКИЙ РОУТ ТЕПЕРЬ В КОНЦЕ!)
@router.get("/video/{video_id}")
async def get_video(video_id: str):
    return {"url": get_video_url(video_id)}

# 4️⃣ Удаление видео
@router.delete("/video/{video_id}")
async def remove(video_id: str):
    delete_video(video_id)
    return {"message": f"Видео {video_id} удалено"}
