from fastapi import FastAPI
from app.api.endpoints import videos, editor

app = FastAPI(title="FFmpeg Backend")

# Подключаем эндпоинты
app.include_router(videos.router, prefix="/videos")
app.include_router(editor.router, prefix="/editor")

# Корневой эндпоинт
@app.get("/")
def root():
    return {"message": "FFmpeg API работает!"}
