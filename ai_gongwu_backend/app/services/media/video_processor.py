"""音视频处理模块。

这个文件负责把“原始媒体文件”转换成“可以评分的结构化输入”。

视频处理包含两条线：
1. 内容线：抽音频 -> Whisper 转文字
2. 表现线：OpenCV 做一个非常轻量的人脸稳定性分析

最终输出一个统一的 MediaExtractionResult，
供后面的评分流程使用。
"""

import logging
from pathlib import Path
import subprocess
import tempfile

from app.core.config import settings
from app.models.schemas import MediaExtractionResult
from app.services.media.audio_transcriber import get_transcriber

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_audio_path: str) -> str:
    """使用 ffmpeg 从视频中提取单声道 16k 音频。

    16k / 单声道是 ASR 很常见的输入格式，通常更省资源。
    """

    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        output_audio_path,
    ]

    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # 返回音频路径，供后续 Whisper 使用。
        return output_audio_path
    except FileNotFoundError as exc:
        raise RuntimeError("系统未安装 ffmpeg，无法处理视频文件。") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("音频提取失败，请检查视频文件格式或完整性。") from exc


def analyze_facial_behavior(video_path: str) -> str:
    """执行一个轻量级的视觉分析。

    注意：
    这里不是做严肃的情绪识别，也不是做人脸身份鉴权。
    它只是非常简单地观察：
    - 是否能检测到脸
    - 头部上下位置变化是否过于频繁

    所以返回结果只能当“弱观察”，不能当强结论。
    """

    if not settings.ENABLE_VISUAL_ANALYSIS:
        return "已关闭视觉分析。"

    try:
        import cv2
    except ImportError:
        logger.warning("未安装 OpenCV，跳过视觉分析。")
        return "视觉分析依赖未安装，已跳过。"

    logger.info("正在执行视觉行为分析: %s", video_path)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    # 用 OpenCV 打开视频流，逐帧读取。
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"OpenCV 无法打开视频流: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps != fps:
        fps = 25.0

    # 没必要逐帧分析，这里按“每秒约 2 帧”的节奏抽样，节省计算。
    frame_step = max(1, int(fps / 2))
    frames_processed = 0
    faces_detected = 0
    head_movements = 0
    last_center_y = None

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frames_processed += 1
            if frames_processed % frame_step != 0:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
            )

            if len(faces) == 0:
                continue

            faces_detected += 1
            x, y, w, h = faces[0]
            frame_height = frame.shape[0]
            center_y = (y + h / 2.0) / frame_height

            # 简单比较连续两次检测到的人脸中心点高度变化，
            # 估算头部晃动程度。
            if last_center_y is not None and abs(center_y - last_center_y) > 0.05:
                head_movements += 1
            last_center_y = center_y
    finally:
        cap.release()

    if faces_detected == 0:
        return "视频中未检测到清晰人脸，无法稳定评估仪态。"

    movement_ratio = head_movements / faces_detected
    if movement_ratio > 0.3:
        return "考生头部晃动较多，可能存在紧张表现。"
    if movement_ratio < 0.05:
        return "考生仪态较稳定，整体表现较为从容。"
    return "考生肢体语言整体自然，无明显异常。"


def process_video(video_path: str) -> MediaExtractionResult:
    """处理视频文件。

    步骤如下：
    1. 先把视频里的音频提取出来
    2. 用 Whisper 转成文字
    3. 用 OpenCV 补一个轻量视觉观察
    4. 返回统一结构
    """

    temp_audio_path = None
    try:
        # NamedTemporaryFile(delete=False) 让我们拿到一个真实文件路径，
        # 便于 ffmpeg 和 Whisper 使用。
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_audio_path = temp_audio.name

        extract_audio(video_path, temp_audio_path)
        transcriber = get_transcriber()
        transcript = transcriber.transcribe(temp_audio_path).strip()
        if not transcript:
            # 即使没识别到内容，也返回兜底文本，防止下游出现空字符串异常。
            transcript = "（未能识别到任何有效的人声作答）"

        visual_observation = analyze_facial_behavior(video_path)
        return MediaExtractionResult(
            transcript=transcript,
            source="video",
            visual_observation=visual_observation,
        )
    finally:
        # 及时清理临时音频文件，避免服务器堆积大量 wav。
        if temp_audio_path:
            temp_audio = Path(temp_audio_path)
            if temp_audio.exists():
                temp_audio.unlink(missing_ok=True)


def process_audio(audio_path: str) -> MediaExtractionResult:
    """处理纯音频文件。"""

    transcriber = get_transcriber()
    transcript = transcriber.transcribe(audio_path).strip()
    if not transcript:
        transcript = "（未能识别到任何有效的人声作答）"

    return MediaExtractionResult(
        transcript=transcript,
        source="audio",
        visual_observation=None,
    )
