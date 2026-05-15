from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import uuid

from fastapi import HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from app.core.config import settings

ALLOWED_EXTENSIONS = {
    ".webm": "video/webm",
    ".mp4": "video/mp4",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".mov": "video/quicktime",
}
VIDEO_EXTENSIONS = {".webm", ".mp4", ".mov"}
CHUNK_SIZE = 1024 * 1024


def _storage_root() -> Path:
    root = settings.media_storage_root
    return root if root.is_absolute() else settings.backend_root / root


def original_media_dir() -> Path:
    path = _storage_root() / "original"
    path.mkdir(parents=True, exist_ok=True)
    return path


def optimized_media_dir() -> Path:
    path = _storage_root() / "optimized"
    path.mkdir(parents=True, exist_ok=True)
    return path


def uploads_dir() -> Path:
    return settings.backend_root / "uploads"


def sanitize_filename(raw_name: str) -> str:
    safe_name = "".join(ch for ch in str(raw_name or "") if ch.isascii() and (ch.isalnum() or ch in {"-", "_", "."}))
    return safe_name or "recording.webm"


def _magic_extension(content: bytes, fallback: str = "") -> str:
    head = content[:32]
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return fallback if fallback in {".mp4", ".m4a", ".mov"} else ".mp4"
    if head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return ".mp3"
    if head.startswith(b"RIFF") and b"WAVE" in head[:16]:
        return ".wav"
    if head.startswith(b"OggS"):
        return ".ogg"
    return fallback


def _is_video_type(media_type: str, extension: str, source: str = "") -> bool:
    value = f"{media_type} {source}".lower()
    return "video" in value or extension in VIDEO_EXTENSIONS


def _resolved_mime(media_type: str, extension: str, source: str = "") -> str:
    media_type = str(media_type or "").split(";", 1)[0].strip().lower()
    if media_type in {"audio", "video", "application/octet-stream", ""}:
        if extension in {".mp3", ".m4a", ".wav", ".ogg"} or ("audio" in str(source or "").lower() and extension == ".webm"):
            return ALLOWED_EXTENSIONS.get(extension, "audio/webm")
        return ALLOWED_EXTENSIONS.get(extension, "video/webm")
    return media_type


def validate_media_upload(content: bytes, filename: str, media_type: str = "", source: str = "") -> tuple[str, str, bool]:
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > settings.media_upload_max_bytes:
        raise HTTPException(status_code=413, detail="上传文件过大")

    original_name = sanitize_filename(filename)
    fallback_ext = Path(original_name).suffix.lower()
    extension = _magic_extension(content, fallback_ext)
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的录音/视频格式")

    mime = _resolved_mime(media_type, extension, source)
    if not (mime.startswith("audio/") or mime.startswith("video/")):
        raise HTTPException(status_code=400, detail="不支持的媒体 MIME 类型")
    return extension, mime, _is_video_type(mime, extension, source)


def _safe_storage_key(key: str) -> PurePosixPath:
    key_path = PurePosixPath(str(key or ""))
    if key_path.is_absolute() or ".." in key_path.parts:
        raise HTTPException(status_code=400, detail="媒体存储 key 无效")
    return key_path


def _write_original(content: bytes, extension: str) -> tuple[str, Path]:
    storage_key = f"{uuid.uuid4().hex[:2]}/{uuid.uuid4().hex}{extension}"
    key_path = _safe_storage_key(storage_key)
    path = original_media_dir() / Path(*key_path.parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return storage_key, path


def _ffmpeg_binary() -> str:
    configured = str(settings.media_ffmpeg_path or "ffmpeg")
    return configured if Path(configured).is_absolute() else (shutil.which(configured) or configured)


def _probe_media(path: Path) -> bool:
    ffmpeg = _ffmpeg_binary()
    try:
        result = subprocess.run(
            [ffmpeg, "-v", "error", "-i", str(path), "-f", "null", "-"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _lossless_optimize(original_path: Path, storage_key: str, extension: str) -> dict:
    if not settings.media_lossless_optimize_enabled:
        return {"used": False, "reason": "disabled"}
    ffmpeg = _ffmpeg_binary()
    if not shutil.which(ffmpeg) and not Path(ffmpeg).exists():
        return {"used": False, "reason": "ffmpeg_not_found"}

    key_path = _safe_storage_key(storage_key)
    output_path = optimized_media_dir() / Path(*key_path.parts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [ffmpeg, "-y", "-i", str(original_path), "-map", "0", "-c", "copy", "-map_metadata", "-1"]
    if extension in {".mp4", ".m4a", ".mov"}:
        command.extend(["-movflags", "+faststart"])
    command.append(str(output_path))

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except Exception as exc:
        return {"used": False, "reason": "ffmpeg_failed", "error": str(exc)}

    if result.returncode != 0 or not output_path.exists():
        return {"used": False, "reason": "ffmpeg_failed"}
    original_size = original_path.stat().st_size
    optimized_size = output_path.stat().st_size
    if optimized_size >= original_size or not _probe_media(output_path):
        output_path.unlink(missing_ok=True)
        return {
            "used": False,
            "reason": "not_smaller",
            "originalSize": original_size,
            "optimizedSize": optimized_size,
        }
    return {
        "used": True,
        "storageKey": storage_key,
        "originalSize": original_size,
        "optimizedSize": optimized_size,
        "ratio": round(optimized_size / original_size, 4) if original_size else 1,
    }


def save_media_upload(content: bytes, filename: str, media_type: str = "", source: str = "") -> dict:
    extension, mime, is_video = validate_media_upload(content, filename, media_type, source)
    original_name = sanitize_filename(filename)
    sha256 = hashlib.sha256(content).hexdigest()
    storage_key, original_path = _write_original(content, extension)
    optimization = _lossless_optimize(original_path, storage_key, extension)
    playback_key = optimization.get("storageKey") if optimization.get("used") else storage_key
    return {
        "storageKey": storage_key,
        "playbackStorageKey": playback_key,
        "originalFilename": original_name,
        "mediaType": mime,
        "mediaKind": "video" if is_video else "audio",
        "sizeBytes": len(content),
        "sha256": sha256,
        "optimized": optimization,
    }


def media_playback_url(exam_id: str, question_id: str) -> str:
    return f"/api/exam/{exam_id}/media/{question_id}/play"


def media_download_url(exam_id: str, question_id: str) -> str:
    return f"/api/exam/{exam_id}/media/{question_id}/download"


def resolve_media_path(media_record: dict) -> Path | None:
    if not isinstance(media_record, dict):
        return None
    playback_key = str(media_record.get("playbackStorageKey") or "").strip()
    original_key = str(media_record.get("storageKey") or "").strip()
    for root, key in ((optimized_media_dir(), playback_key), (original_media_dir(), original_key)):
        if not key:
            continue
        path = root / Path(*_safe_storage_key(key).parts)
        if path.exists():
            return path

    stored_filename = str(media_record.get("storedFilename") or "").strip()
    if not stored_filename:
        file_url = str(media_record.get("fileUrl") or "").strip()
        stored_filename = Path(file_url).name if file_url else ""
    if stored_filename:
        legacy = uploads_dir() / sanitize_filename(stored_filename)
        if legacy.exists():
            return legacy
    return None


def _iter_file(path: Path, start: int = 0, end: int | None = None):
    with path.open("rb") as fh:
        fh.seek(start)
        remaining = None if end is None else end - start + 1
        while True:
            read_size = CHUNK_SIZE if remaining is None else min(CHUNK_SIZE, remaining)
            if read_size <= 0:
                break
            chunk = fh.read(read_size)
            if not chunk:
                break
            if remaining is not None:
                remaining -= len(chunk)
            yield chunk


def media_response(request: Request, media_record: dict, *, download: bool = False) -> Response:
    path = resolve_media_path(media_record)
    if not path:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    size = path.stat().st_size
    mime = str(media_record.get("mediaType") or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    original_filename = sanitize_filename(media_record.get("originalFilename") or path.name)
    headers = {
        "Accept-Ranges": "bytes",
        "X-Content-Type-Options": "nosniff",
    }
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{original_filename}"'
        return StreamingResponse(_iter_file(path), media_type=mime, headers={**headers, "Content-Length": str(size)})

    range_header = str(request.headers.get("range") or "")
    if range_header.startswith("bytes="):
        raw_range = range_header.replace("bytes=", "", 1).split(",", 1)[0]
        raw_start, _, raw_end = raw_range.partition("-")
        try:
            start = int(raw_start) if raw_start else 0
            end = int(raw_end) if raw_end else size - 1
        except ValueError as exc:
            raise HTTPException(status_code=416, detail="Range 请求无效") from exc
        if start < 0 or end < start or start >= size:
            raise HTTPException(status_code=416, detail="Range 请求超出文件范围")
        end = min(end, size - 1)
        content_length = end - start + 1
        headers.update({
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Content-Length": str(content_length),
        })
        return StreamingResponse(_iter_file(path, start, end), status_code=206, media_type=mime, headers=headers)

    return StreamingResponse(_iter_file(path), media_type=mime, headers={**headers, "Content-Length": str(size)})
