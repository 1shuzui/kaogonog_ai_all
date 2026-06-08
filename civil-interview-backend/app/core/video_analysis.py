"""
这个文件做视频行为的轻量分析；如果 OpenCV 或视频文件不可用，它会返回可读提示，避免评分链路直接崩掉。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from __future__ import annotations

from pathlib import Path


def analyze_video_behavior(video_path: str) -> str:
    """
    这个函数抽样读取视频帧，只给评分链路补充“入镜是否稳定、距离是否合适”这类仪态观察。

    它故意把 OpenCV 缺失、文件不存在和识别不到人脸都转成中文提示，避免视频分析失败拖垮文字评分。

    @param video_path: 本地视频文件路径；评分服务传入上传后的视频位置，用于抽样分析考生入镜状态。
    @return: 返回一段可直接放进评分上下文的中文观察，不返回结构化分数。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    try:
        import cv2
    except ImportError:
        return "当前环境未安装 OpenCV，无法完成视频动作与表情观察。"

    source = Path(video_path)
    if not source.exists():
        return "视频文件不存在，无法完成动作与表情观察。"

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        return "视频文件无法打开，无法完成动作与表情观察。"

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps != fps:
        fps = 25.0

    frame_step = max(1, int(fps / 2))
    frames_processed = 0
    sample_frames = 0
    faces_detected = 0
    head_movements = 0
    last_center_y = None
    face_area_ratios: list[float] = []

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frames_processed += 1
            if frames_processed % frame_step != 0:
                continue

            sample_frames += 1
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
            frame_height, frame_width = frame.shape[:2]
            center_y = (y + h / 2.0) / max(frame_height, 1)
            face_area_ratios.append((w * h) / max(frame_height * frame_width, 1))

            if last_center_y is not None and abs(center_y - last_center_y) > 0.05:
                head_movements += 1
            last_center_y = center_y
    finally:
        cap.release()

    if sample_frames == 0:
        return "视频帧读取不足，无法完成动作与表情观察。"
    if faces_detected == 0:
        return "视频中未检测到清晰人脸，无法稳定评估仪态与表情管理。"

    detection_ratio = faces_detected / sample_frames
    movement_ratio = head_movements / max(faces_detected, 1)
    avg_face_ratio = sum(face_area_ratios) / len(face_area_ratios) if face_area_ratios else 0.0

    observations = []
    if detection_ratio < 0.45:
        observations.append("考生多次偏离镜头或人脸识别不稳定，建议保持正面入镜和稳定机位。")
    else:
        observations.append("整体入镜较稳定，面部大部分时间保持在画面有效区域内。")

    if avg_face_ratio < 0.035:
        observations.append("人物距离镜头略远，表情细节不够清晰，建议上半身更靠近镜头。")
    elif avg_face_ratio > 0.18:
        observations.append("人物与镜头距离较近，面部信息清晰，但要注意避免压迫感过强。")
    else:
        observations.append("人物与镜头距离基本合适，表情信息可辨识。")

    if movement_ratio > 0.30:
        observations.append("头部晃动较明显，仪态稳定性一般，建议减少左右摆动和频繁低头。")
    elif movement_ratio < 0.08:
        observations.append("头部控制较稳，整体仪态较为从容。")
    else:
        observations.append("肢体与头部动作自然，但仍可进一步增强停顿与眼神稳定度。")

    observations.append("视频观察只作为表达状态补充，不参与内容事实判断。")
    return "".join(observations)
