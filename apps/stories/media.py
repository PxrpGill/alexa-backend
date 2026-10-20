"""Обработка медиа сторисов: мобильная копия картинки и транскод видео (ffmpeg).

Файлы читаются и пишутся через Django storage, ffmpeg работает с временными
копиями — так код не завязан на то, что storage лежит на локальном диске.
"""

import json
import os
import shutil
import subprocess
import tempfile
from io import BytesIO

import pillow_avif  # noqa: F401  — регистрирует кодек AVIF в Pillow
from django.core.files import File
from django.core.files.base import ContentFile
from PIL import Image

from apps.common.images import generate_image_variants

MOBILE_SUFFIX = '-m'
MOBILE_MAX_WIDTH = 750

# (суффикс файла, рамка длинная×короткая сторона, видео-битрейт, maxrate, bufsize, аудио)
VIDEO_PROFILES = {
    'src': ('-src', 1920, 1080, '3500k', '4000k', '8000k', '128k'),
    'mobile': (MOBILE_SUFFIX, 1280, 720, '1500k', '1800k', '3000k', '96k'),
}
POSTER_SUFFIX = '-poster'
POSTER_QUALITY = 85

FFMPEG_TIMEOUT = 15 * 60
FFPROBE_TIMEOUT = 30


class MediaProcessingError(Exception):
    """ffmpeg/ffprobe не смог обработать файл (или не установлен)."""


class StoredFile:
    """Файл в storage по имени — то, что build_picture_format ждёт от FieldFile."""

    def __init__(self, storage, name):
        self.storage = storage
        self.name = name

    def __bool__(self):
        return bool(self.name)

    @property
    def url(self):
        return self.storage.url(self.name)


def mobile_copy_name(name):
    base, ext = os.path.splitext(name)
    return f'{base}{MOBILE_SUFFIX}{ext}'


def get_mobile_copy(field_file):
    """Мобильная копия картинки, если она уже сгенерирована, иначе None."""
    if not field_file:
        return None
    name = mobile_copy_name(field_file.name)
    if not field_file.storage.exists(name):
        return None
    return StoredFile(field_file.storage, name)


def process_story_image(field_file):
    """webp/avif оригинала + уменьшенная до MOBILE_MAX_WIDTH копия со своими webp/avif."""
    generate_image_variants(field_file)
    mobile = _generate_mobile_copy(field_file)
    generate_image_variants(mobile)


def _generate_mobile_copy(field_file):
    storage = field_file.storage
    name = mobile_copy_name(field_file.name)

    with storage.open(field_file.name, 'rb') as source:
        image = Image.open(source)
        image.load()
    image_format = image.format or 'JPEG'

    if image.width > MOBILE_MAX_WIDTH:
        height = round(image.height * MOBILE_MAX_WIDTH / image.width)
        image = image.resize((MOBILE_MAX_WIDTH, height), Image.LANCZOS)
    if image_format == 'JPEG' and image.mode != 'RGB':
        image = image.convert('RGB')

    buffer = BytesIO()
    image.save(buffer, format=image_format, quality=90)
    buffer.seek(0)
    if storage.exists(name):
        storage.delete(name)
    storage.save(name, ContentFile(buffer.read()))
    return StoredFile(storage, name)


def probe_duration(path):
    """Длительность ролика в секундах; None, если контейнер её не сообщает.

    MediaProcessingError — файл не читается как видео или нет ffprobe.
    """
    output = _run([
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'format=duration:stream=duration,codec_type',
        '-of', 'json', path,
    ], timeout=FFPROBE_TIMEOUT)
    try:
        info = json.loads(output)
    except ValueError as exc:
        raise MediaProcessingError('ffprobe вернул некорректный ответ') from exc

    if not info.get('streams'):
        raise MediaProcessingError('В файле нет видеодорожки')

    for raw in (info.get('format', {}).get('duration'), info['streams'][0].get('duration')):
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def probe_uploaded_duration(uploaded_file):
    """probe_duration для загруженного в форму файла (в памяти или во временном файле)."""
    if hasattr(uploaded_file, 'temporary_file_path'):
        return probe_duration(uploaded_file.temporary_file_path())

    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp.flush()
        uploaded_file.seek(0)
        return probe_duration(tmp.name)


def transcode_story_video(field_file):
    """Транскод в H.264 + AAC mp4 с faststart в двух размерах и постер из первого кадра.

    Возвращает имена сохранённых в storage файлов:
    {'video_src': ..., 'video_mobile': ..., 'video_poster': ...}.
    """
    storage = field_file.storage
    base, ext = os.path.splitext(field_file.name)
    tmp_dir = tempfile.mkdtemp(prefix='story-video-')
    try:
        source_path = os.path.join(tmp_dir, f'source{ext}')
        with storage.open(field_file.name, 'rb') as source, open(source_path, 'wb') as tmp:
            shutil.copyfileobj(source, tmp)

        result = {}
        for profile, (suffix, long_side, short_side, *rates) in VIDEO_PROFILES.items():
            out_path = os.path.join(tmp_dir, f'{profile}.mp4')
            _run(_transcode_command(source_path, out_path, long_side, short_side, *rates))
            result[f'video_{profile}'] = _save(storage, f'{base}{suffix}.mp4', out_path)

        frame_path = os.path.join(tmp_dir, 'poster.png')
        _run([
            'ffmpeg', '-y', '-v', 'error', '-i', source_path,
            '-frames:v', '1', '-vf', _scale_filter(1920, 1080), frame_path,
        ])
        poster_path = os.path.join(tmp_dir, 'poster.webp')
        with Image.open(frame_path) as frame:
            frame.convert('RGB').save(poster_path, format='WEBP', quality=POSTER_QUALITY)
        result['video_poster'] = _save(storage, f'{base}{POSTER_SUFFIX}.webp', poster_path)
        return result
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _scale_filter(long_side, short_side):
    """Вписать кадр в рамку long×short с учётом ориентации, без апскейла.

    Для вертикального ролика рамка — short×long (1080×1920), для горизонтального —
    long×short. Чётные размеры обязательны для yuv420p.
    """
    width = f"if(gte(iw,ih),min(iw,{long_side}),min(iw,{short_side}))"
    height = f"if(gte(iw,ih),min(ih,{short_side}),min(ih,{long_side}))"
    return (
        f"scale=w='{width}':h='{height}'"
        ':force_original_aspect_ratio=decrease:force_divisible_by=2'
    )


def _transcode_command(source, out, long_side, short_side, bitrate, maxrate, bufsize, audio):
    return [
        'ffmpeg', '-y', '-v', 'error', '-i', source,
        '-map', '0:v:0', '-map', '0:a:0?',
        '-vf', _scale_filter(long_side, short_side),
        '-c:v', 'libx264', '-preset', 'veryfast', '-profile:v', 'high',
        '-pix_fmt', 'yuv420p',
        '-b:v', bitrate, '-maxrate', maxrate, '-bufsize', bufsize,
        '-c:a', 'aac', '-b:a', audio, '-ac', '2',
        '-movflags', '+faststart',
        out,
    ]


def _save(storage, name, path):
    if storage.exists(name):
        storage.delete(name)
    with open(path, 'rb') as fh:
        return storage.save(name, File(fh))


def _run(command, timeout=FFMPEG_TIMEOUT):
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except FileNotFoundError as exc:
        raise MediaProcessingError(f'{command[0]} не установлен') from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaProcessingError(f'{command[0]}: превышено время обработки') from exc
    if completed.returncode != 0:
        raise MediaProcessingError(
            f'{command[0]} завершился с кодом {completed.returncode}: '
            f'{completed.stderr.strip()[-500:]}'
        )
    return completed.stdout
