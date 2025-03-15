from fastapi import FastAPI
from app.api.endpoints import videos

app = FastAPI(title="FFmpeg Backend")

# Подключаем эндпоинты
app.include_router(videos.router, prefix="/videos")

# Корневой эндпоинт
@app.get("/")
def root():
    return {"message": "FFmpeg API работает!"}
