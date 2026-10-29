"""Canonical answer media, with read compatibility for legacy scoring JSON."""
from pathlib import Path


def normalize_media_type(value: str, filename: str = "") -> str:
    kind = str(value or "").strip().lower().split(";", 1)[0]
    if kind.startswith(("audio/", "video/")):
        return kind
    suffix = Path(str(filename or "").split("?", 1)[0]).suffix.lower()
    if kind == "video" or suffix in {".mp4", ".mov", ".m4v"}:
        return "video/webm" if suffix == ".webm" else "video/mp4"
    if kind == "audio" or suffix in {".mp3", ".m4a", ".aac", ".wav", ".ogg"}:
        return {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".wav": "audio/wav", ".ogg": "audio/ogg"}.get(suffix, "audio/webm")
    return "video/webm" if suffix == ".webm" else kind or "application/octet-stream"


def answer_media_record(answer) -> dict:
    if answer is None:
        return {}
    score = answer.score_result if isinstance(answer.score_result, dict) else {}
    legacy = score.get("mediaRecord") if isinstance(score.get("mediaRecord"), dict) else {}
    current = answer.media_record if isinstance(answer.media_record, dict) else {}
    record = {**legacy, **current}
    if record:
        record["mediaType"] = normalize_media_type(record.get("mediaType"), record.get("originalFilename") or record.get("fileUrl"))
    return record
