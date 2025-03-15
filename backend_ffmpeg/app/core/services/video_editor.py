import subprocess
import os
import uuid
from fastapi import HTTPException
from app.core.services.s3 import s3, settings, upload_video
import cv2


def cut_video(video_id: str, start_time: float, end_time: float, format: str = None) -> dict:
    """
    Нарезает видео с помощью FFmpeg с использованием NVIDIA NVENC (h264_nvenc).

    :param video_id: Имя исходного видео в S3
    :param start_time: Начало нарезки (секунды)
    :param end_time: Конец нарезки (секунды)
    :param format: Формат выходного видео (если None — сохраняем оригинальный)
    :return: JSON-ответ (URL или ошибка)
    """

    try:
        # 1️⃣ ВАЛИДАЦИЯ ДАННЫХ
        if start_time < 0 or end_time <= start_time:
            raise HTTPException(status_code=400, detail="⛔ Неверные временные метки: `start_time` должен быть >= 0, `end_time` должен быть больше `start_time`.")

        unique_id = uuid.uuid4().hex  # Генерируем уникальный ID
        input_file = f"/tmp/{video_id}"

        # 2️⃣ Получаем оригинальный формат файла
        if format is None:
            format = video_id.split(".")[-1]  # Берём расширение оригинального файла

        output_file = f"/tmp/{unique_id}.{format}"  # Файл с новым форматом

        # 3️⃣ ПРОВЕРЯЕМ, СУЩЕСТВУЕТ ЛИ ВИДЕО В MinIO
        try:
            response = s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=video_id)
            file_size = response["ContentLength"]
            if file_size == 0:
                raise HTTPException(status_code=400, detail=f"⚠️ Видео `{video_id}` пустое.")
        except Exception:
            raise HTTPException(status_code=404, detail=f"❌ Видео `{video_id}` не найдено в S3!")

        # 4️⃣ Скачиваем видео из S3
        try:
            print(f"🚀 Скачивание видео: {video_id}")
            s3.download_file(settings.S3_BUCKET_NAME, video_id, input_file)
            print(f"✅ Видео скачано: {input_file}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка скачивания видео: {str(e)}")

        # 5️⃣ Выполняем нарезку через FFmpeg с H.264 NVENC (аппаратное ускорение на видеокарте)
        command = [
            "ffmpeg", "-y", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda",  # Включаем NVENC
            "-i", input_file,
            "-ss", str(start_time),
            "-to", str(end_time),
            "-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "5M",  # Кодек NVENC
            "-c:a", "aac", "-b:a", "128k",  # Аудио кодек AAC
            output_file
        ]

        print(f"🔥 FFmpeg команда: {' '.join(command)}")  # Логируем команду FFmpeg

        try:
            subprocess.run(command, check=True)
            print(f"✅ Видео нарезано: {output_file}")
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка FFmpeg: {str(e)}")

        # 6️⃣ Загружаем нарезанное видео обратно в S3
        try:
            with open(output_file, "rb") as f:
                upload_video(f, f"{unique_id}.{format}")
            print(f"✅ Видео загружено в S3: {unique_id}.{format}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка загрузки в S3: {str(e)}")

        # 7️⃣ Удаляем временные файлы
        os.remove(input_file)
        os.remove(output_file)

        # 8️⃣ Возвращаем JSON-ответ
        return {"message": "✅ Видео успешно нарезано!", "url": f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET_NAME}/{unique_id}.{format}"}

    except HTTPException as e:
        # Если поймали `HTTPException`, просто возвращаем её
        raise e

    except Exception as e:
        # Ловим любые другие ошибки и отдаём 500
        raise HTTPException(status_code=500, detail=f"❌ Внутренняя ошибка сервера: {str(e)}")



def convert_video(video_id: str, target_format: str) -> dict:
    """
    Конвертирует видео в другой формат с помощью FFmpeg и NVENC.

    :param video_id: Имя исходного видео в S3
    :param target_format: Формат конвертации (mp4, avi, mov, mkv)
    :return: JSON-ответ (URL или ошибка)
    """

    try:
        # 1️⃣ ВАЛИДАЦИЯ ДАННЫХ
        allowed_formats = ["mp4", "avi", "mov", "mkv"]
        if target_format.lower() not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"⛔ Неподдерживаемый формат `{target_format}`. Доступны: {', '.join(allowed_formats)}"
            )

        unique_id = uuid.uuid4().hex  # Генерируем уникальный ID
        input_file = f"/tmp/{video_id}"
        output_file = f"/tmp/{unique_id}.{target_format}"  # Файл с новым форматом

        # 2️⃣ ПРОВЕРЯЕМ, СУЩЕСТВУЕТ ЛИ ВИДЕО В MinIO
        try:
            response = s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=video_id)
            file_size = response["ContentLength"]
            if file_size == 0:
                raise HTTPException(status_code=400, detail=f"⚠️ Видео `{video_id}` пустое.")
        except Exception:
            raise HTTPException(status_code=404, detail=f"❌ Видео `{video_id}` не найдено в S3!")

        # 3️⃣ Скачиваем видео из S3
        try:
            print(f"🚀 Скачивание видео: {video_id}")
            s3.download_file(settings.S3_BUCKET_NAME, video_id, input_file)
            print(f"✅ Видео скачано: {input_file}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка скачивания видео: {str(e)}")

        # 4️⃣ Выполняем конвертацию через FFmpeg с H.264 NVENC
        command = [
            "ffmpeg", "-y", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda",  # Включаем NVENC
            "-i", input_file,
            "-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "5M",  # Кодек NVENC
            "-c:a", "aac", "-b:a", "128k",  # Аудио кодек AAC
            output_file
        ]

        print(f"🔥 FFmpeg команда: {' '.join(command)}")  # Логируем команду FFmpeg

        try:
            subprocess.run(command, check=True)
            print(f"✅ Видео конвертировано: {output_file}")
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка FFmpeg: {str(e)}")

        # 5️⃣ Загружаем сконвертированное видео обратно в S3
        try:
            with open(output_file, "rb") as f:
                upload_video(f, f"{unique_id}.{target_format}")
            print(f"✅ Видео загружено в S3: {unique_id}.{target_format}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка загрузки в S3: {str(e)}")

        # 6️⃣ Удаляем временные файлы
        os.remove(input_file)
        os.remove(output_file)

        # 7️⃣ Возвращаем JSON-ответ
        return {"message": "✅ Видео успешно конвертировано!", "url": f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET_NAME}/{unique_id}.{target_format}"}

    except HTTPException as e:
        # Если поймали `HTTPException`, просто возвращаем её
        raise e

    except Exception as e:
        # Ловим любые другие ошибки и отдаём 500
        raise HTTPException(status_code=500, detail=f"❌ Внутренняя ошибка сервера: {str(e)}")


def resize_video(video_id: str, resolution: str, format: str = "mp4") -> dict:
    """
    Изменяет разрешение видео с помощью FFmpeg и NVENC.

    :param video_id: Имя исходного видео в S3
    :param resolution: Новое разрешение (например, "1280x720")
    :param format: Формат выходного видео (по умолчанию MP4)
    :return: JSON-ответ (URL или ошибка)
    """

    try:
        # 1️⃣ ВАЛИДАЦИЯ ДАННЫХ
        try:
            width, height = map(int, resolution.lower().split("x"))
            if width <= 0 or height <= 0:
                raise ValueError
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"⛔ Неверный формат разрешения '{resolution}'. Используйте '1280x720'."
            )

        unique_id = uuid.uuid4().hex  # Генерируем уникальный ID
        input_file = f"/tmp/{video_id}"
        output_file = f"/tmp/{unique_id}.{format}"  # Файл с новым разрешением

        # 2️⃣ ПРОВЕРЯЕМ, СУЩЕСТВУЕТ ЛИ ВИДЕО В MinIO
        try:
            response = s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=video_id)
            file_size = response["ContentLength"]
            if file_size == 0:
                raise HTTPException(status_code=400, detail=f"⚠️ Видео `{video_id}` пустое.")
        except Exception:
            raise HTTPException(status_code=404, detail=f"❌ Видео `{video_id}` не найдено в S3!")

        # 3️⃣ Скачиваем видео из S3
        try:
            print(f"🚀 Скачивание видео: {video_id}")
            s3.download_file(settings.S3_BUCKET_NAME, video_id, input_file)
            print(f"✅ Видео скачано: {input_file}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка скачивания видео: {str(e)}")

        # 4️⃣ Проверяем, поддерживается ли `scale_cuda`
        scale_filter = f"scale_cuda={width}:{height}:force_original_aspect_ratio=decrease" if check_scale_cuda() else f"scale={width}:{height}:force_original_aspect_ratio=decrease"

        # 5️⃣ Изменяем разрешение с NVENC (CUDA) и корректируем DAR
        command = [
            "ffmpeg", "-y", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda",  # Аппаратное ускорение
            "-i", input_file,
            "-vf", scale_filter,  # Используем правильный формат для scale
            "-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "5M",  # Кодек NVENC
            "-c:a", "aac", "-b:a", "128k",  # Аудио кодек AAC
            output_file
        ]

        print(f"🔥 FFmpeg команда: {' '.join(command)}")  # Логируем команду FFmpeg

        try:
            subprocess.run(command, check=True)
            print(f"✅ Видео изменено: {output_file}")
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка FFmpeg: {str(e)}")

        # 6️⃣ Загружаем изменённое видео обратно в S3
        try:
            with open(output_file, "rb") as f:
                upload_video(f, f"{unique_id}.{format}")
            print(f"✅ Видео загружено в S3: {unique_id}.{format}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка загрузки в S3: {str(e)}")

        # 7️⃣ Удаляем временные файлы
        os.remove(input_file)
        os.remove(output_file)

        # 8️⃣ Возвращаем JSON-ответ
        return {"message": "✅ Видео успешно изменено!", "url": f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET_NAME}/{unique_id}.{format}"}

    except HTTPException as e:
        # Если поймали `HTTPException`, просто возвращаем её
        raise e

    except Exception as e:
        # Ловим любые другие ошибки и отдаём 500
        raise HTTPException(status_code=500, detail=f"❌ Внутренняя ошибка сервера: {str(e)}")
    

def check_scale_cuda() -> bool:
    """
    Проверяет, поддерживается ли `scale_cuda` на текущем FFmpeg.
    """
    try:
        result = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
        return "scale_cuda" in result.stdout
    except Exception:
        return False  # Если ошибка, используем `scale`


def get_video_resolution(file_path: str):
    """
    Получает разрешение видео с помощью FFmpeg.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                file_path
            ],
            capture_output=True,
            text=True,
            check=True
        )
        width, height = map(int, result.stdout.strip().split(","))
        return width, height
    except Exception as e:
        raise RuntimeError(f"❌ Ошибка при получении разрешения видео: {str(e)}")

def crop_video(video_id: str, x: int, y: int, width: int, height: int, format: str = "mp4") -> dict:
    """
    Обрезает видео с помощью FFmpeg и NVENC.

    :param video_id: Имя исходного видео в S3
    :param x: Начальная координата X (в пикселях)
    :param y: Начальная координата Y (в пикселях)
    :param width: Ширина обрезанного видео (в пикселях)
    :param height: Высота обрезанного видео (в пикселях)
    :param format: Формат выходного видео (по умолчанию MP4)
    :return: JSON-ответ (URL или ошибка)
    """

    try:
        # 1️⃣ ВАЛИДАЦИЯ ДАННЫХ
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise HTTPException(
                status_code=400,
                detail="⛔ Ошибка: x, y должны быть >= 0, а width и height > 0."
            )

        unique_id = uuid.uuid4().hex  # Генерируем уникальный ID
        input_file = f"/tmp/{video_id}"
        output_file = f"/tmp/{unique_id}.{format}"  # Файл с обрезанным видео

        # 2️⃣ ПРОВЕРЯЕМ, СУЩЕСТВУЕТ ЛИ ВИДЕО В MinIO
        try:
            response = s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=video_id)
            file_size = response["ContentLength"]
            if file_size == 0:
                raise HTTPException(status_code=400, detail=f"⚠️ Видео `{video_id}` пустое.")
        except Exception:
            raise HTTPException(status_code=404, detail=f"❌ Видео `{video_id}` не найдено в S3!")

        # 3️⃣ Скачиваем видео из S3
        try:
            print(f"🚀 Скачивание видео: {video_id}")
            s3.download_file(settings.S3_BUCKET_NAME, video_id, input_file)
            print(f"✅ Видео скачано: {input_file}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка скачивания видео: {str(e)}")

        # 4️⃣ **Получаем оригинальное разрешение видео**
        original_width, original_height = get_video_resolution(input_file)
        print(f"📏 Оригинальный размер видео: {original_width}x{original_height}")

        # 5️⃣ **Проверяем, не выходит ли `crop` за границы**
        if x + width > original_width or y + height > original_height:
            raise HTTPException(
                status_code=400,
                detail=f"⛔ Ошибка: Обрезаемая область ({width}x{height} с X={x}, Y={y}) выходит за пределы видео ({original_width}x{original_height})"
            )

        # 6️⃣ Обрезаем видео с помощью FFmpeg
        crop_filter = f"crop={width}:{height}:{x}:{y}"

        command = [
            "ffmpeg", "-y", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda",  # Аппаратное ускорение
            "-i", input_file,
            "-vf", crop_filter,  # Обрезка видео
            "-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "5M",  # Кодек NVENC
            "-c:a", "aac", "-b:a", "128k",  # Аудио кодек AAC
            "-report",  # Генерируем лог-файл FFmpeg
            output_file
        ]

        print(f"🔥 FFmpeg команда: {' '.join(command)}")  # Логируем команду FFmpeg

        try:
            subprocess.run(command, check=True)
            print(f"✅ Видео обрезано: {output_file}")
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка FFmpeg: {str(e)}")

        # 7️⃣ Загружаем обрезанное видео обратно в S3
        try:
            with open(output_file, "rb") as f:
                upload_video(f, f"{unique_id}.{format}")
            print(f"✅ Видео загружено в S3: {unique_id}.{format}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка загрузки в S3: {str(e)}")

        # 8️⃣ Удаляем временные файлы
        os.remove(input_file)
        os.remove(output_file)

        # 9️⃣ Возвращаем JSON-ответ
        return {"message": "✅ Видео успешно обрезано!", "url": f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET_NAME}/{unique_id}.{format}"}

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Внутренняя ошибка сервера: {str(e)}")
    


def calculate_size(video_path, target_width, target_height):
    """
    Вычисляет размеры для масштабирования и обрезки видео под нужный регион без растяжения.
    """
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    scale_w = target_width / width
    scale_h = target_height / height
    scale = max(scale_w, scale_h)

    new_width = int(width * scale)
    new_height = int(height * scale)

    crop_x = (new_width - target_width) // 2 if new_width > target_width else 0
    crop_y = (new_height - target_height) // 2 if new_height > target_height else 0

    return new_width, new_height, crop_x, crop_y


def merge_videos(main_video_id: str, background_video_id: str, format: str = "mp4") -> dict:
    """
    Объединяет основное видео и фон в TikTok-формате (9:16).

    :param main_video_id: Имя основного видео в S3
    :param background_video_id: Имя фонового видео в S3
    :param format: Формат выходного видео (по умолчанию MP4)
    :return: JSON-ответ (URL или ошибка)
    """

    try:
        unique_id = uuid.uuid4().hex  # Генерируем уникальный ID
        output_file = f"/tmp/{unique_id}.{format}"  # Финальный файл

        main_video_path = f"/tmp/{main_video_id}"
        background_video_path = f"/tmp/{background_video_id}"

        # 1️⃣ Скачиваем видео из S3
        try:
            print(f"🚀 Скачивание основного видео: {main_video_id}")
            s3.download_file(settings.S3_BUCKET_NAME, main_video_id, main_video_path)
            print(f"✅ Видео скачано: {main_video_path}")

            print(f"🚀 Скачивание фонового видео: {background_video_id}")
            s3.download_file(settings.S3_BUCKET_NAME, background_video_id, background_video_path)
            print(f"✅ Видео скачано: {background_video_path}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка скачивания видео: {str(e)}")

        # 2️⃣ **Определяем TikTok-формат (1080x1920)**
        tiktok_width, tiktok_height = 1080, 1920
        main_region_height = int(tiktok_height * 0.5)  # Верхняя часть
        bg_region_height = tiktok_height - main_region_height  # Нижняя часть

        # 3️⃣ **Определяем размеры видео**
        main_width, main_height, main_crop_x, main_crop_y = calculate_size(main_video_path, tiktok_width, main_region_height)
        bg_width, bg_height, bg_crop_x, bg_crop_y = calculate_size(background_video_path, tiktok_width, bg_region_height)

        # 4️⃣ **Формируем FFmpeg команду**
        cmd = [
            "ffmpeg", "-y",
            "-loglevel", "warning",  # ⚡️ Уменьшение вывода FFmpeg
            "-i", main_video_path,
            "-stream_loop", "-1", "-i", background_video_path,
            "-filter_complex",
            (
                f"[0:v]scale={main_width}:{main_height},crop={tiktok_width}:{main_region_height}:{main_crop_x}:{main_crop_y}[v0];"
                f"[1:v]scale={bg_width}:{bg_height},crop={tiktok_width}:{bg_region_height}:{bg_crop_x}:{bg_crop_y}[v1];"
                "[v0][v1]vstack=inputs=2[vout]"
            ),
            "-map", "[vout]",
            "-map", "0:a?",
            "-c:v", "h264_nvenc",
            "-preset", "p1",
            "-cq", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-aspect", "9:16",
            "-shortest",
            output_file
        ]

        print(f"🔥 FFmpeg команда: {' '.join(cmd)}")

        # 5️⃣ **Запускаем FFmpeg**
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Видео объединено: {output_file}")
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка FFmpeg: {str(e)}")

        # 6️⃣ **Загружаем результат в S3**
        try:
            with open(output_file, "rb") as f:
                upload_video(f, f"{unique_id}.{format}")
            print(f"✅ Видео загружено в S3: {unique_id}.{format}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка загрузки в S3: {str(e)}")

        # 7️⃣ **Удаляем временные файлы**
        os.remove(main_video_path)
        os.remove(background_video_path)
        os.remove(output_file)

        # 8️⃣ **Возвращаем ссылку**
        return {"message": "✅ Видео успешно объединено!", "url": f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET_NAME}/{unique_id}.{format}"}

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Внутренняя ошибка сервера: {str(e)}")
