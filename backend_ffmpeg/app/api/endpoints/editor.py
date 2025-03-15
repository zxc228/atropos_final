from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from app.core.services.video_editor import cut_video, convert_video, resize_video, crop_video, merge_videos

router = APIRouter()

# 📌 Модель запроса
class CutRequest(BaseModel):
    video_id: str
    start_time: float
    end_time: float
    format: str = "mp4"

# 📌 Эндпоинт нарезки видео
@router.post("/cut")
async def cut_video_endpoint(request: CutRequest):
    try:
        video_url = cut_video(
            video_id=request.video_id,
            start_time=request.start_time,
            end_time=request.end_time,
            format=request.format
        )
        return {"url": video_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# 📌 Модель запроса
class ConvertRequest(BaseModel):
    video_id: str
    target_format: str

# 📌 Эндпоинт для конвертации видео
@router.post("/convert")
async def convert_video_endpoint(request: ConvertRequest):
    try:
        video_url = convert_video(
            video_id=request.video_id,
            target_format=request.target_format
        )
        return {"url": video_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

class ResizeRequest(BaseModel):
    video_id: str
    resolution: str  # Например, "1280x720"
    format: str = "mp4"

# 📌 Эндпоинт для изменения разрешения видео
@router.post("/resize")
async def resize_video_endpoint(request: ResizeRequest):
    try:
        video_url = resize_video(
            video_id=request.video_id,
            resolution=request.resolution,
            format=request.format
        )
        return {"url": video_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CropRequest(BaseModel):
    video_id: str = Field(..., example="example.mp4")
    x: int = Field(..., ge=0, example=100)
    y: int = Field(..., ge=0, example=50)
    width: int = Field(..., gt=0, example=1280)
    height: int = Field(..., gt=0, example=720)
    format: str = Field("mp4", example="mp4")

@router.post("/crop")
async def crop_video_endpoint(request: CropRequest):
    """
    Эндпоинт обрезки видео.
    """
    try:
        video_url = crop_video(
            video_id=request.video_id,
            x=request.x,
            y=request.y,
            width=request.width,
            height=request.height,
            format=request.format
        )
        return {"message": "✅ Видео успешно обрезано!", "url": video_url}
    except HTTPException as e:
        raise e  # Возвращаем ошибки FastAPI (например, если видео не найдено)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Внутренняя ошибка сервера: {str(e)}")
    


class MergeRequest(BaseModel):
    main_video_id: str
    background_video_id: str
    format: str = "mp4"

@router.post("/merge")
async def merge_video_endpoint(request: MergeRequest):
    """
    Эндпоинт объединения видео в TikTok-формате.
    """
    try:
        video_url = merge_videos(
            main_video_id=request.main_video_id,
            background_video_id=request.background_video_id,
            format=request.format
        )
        return {"message": "✅ Видео успешно объединено!", "url": video_url}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Внутренняя ошибка сервера: {str(e)}")