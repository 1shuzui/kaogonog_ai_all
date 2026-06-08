#!/usr/bin/env python3
"""
这个脚本用样本音频比较 ASR 效果；调 FunASR 参数时先看它输出的错字率和耗时。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
DEFAULT_REPORT_DIR = REPO_ROOT / "reports" / "asr"
ASSET_DIR = BACKEND_ROOT / "assets" / "asr_samples"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.media.audio_transcriber import get_transcriber


@dataclass
class ASRRow:
    """
    ASRRow 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    sample_name: str
    provider: str
    audio_path: str
    raw_text: str
    normalized_text: str
    gold_text: str
    normalized_gold_text: str
    cer: float
    elapsed_seconds: float
    error: str = ""


DEFAULT_SAMPLE_SET = [
    {
        "name": "asr_example",
        "path": str(ASSET_DIR / "asr_example.wav"),
        "url": "https://raw.githubusercontent.com/modelscope/FunASR/main/example/asr_example.wav",
        "gold": "欢迎大家来体验达摩院推出的语音识别模型。",
    },
    {
        "name": "vad_example",
        "path": str(ASSET_DIR / "vad_example.wav"),
        "url": "https://raw.githubusercontent.com/modelscope/FunASR/main/example/vad_example.wav",
        "gold": "北京图书馆欢迎您。",
    },
    {
        "name": "vad_example_clip",
        "path": str(ASSET_DIR / "vad_example_clip.wav"),
        "source_path": str(ASSET_DIR / "vad_example.wav"),
        "gold": "北京图书馆欢迎您。",
        "clip_start": 10,
        "clip_duration": 15,
    },
]


def parse_args() -> argparse.Namespace:
    """
    parse_args 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    parser = argparse.ArgumentParser(description="对比 Whisper 与 FunASR 的小批量 ASR 结果。")
    parser.add_argument(
        "--samples",
        nargs="*",
        default=None,
        help="样本定义 JSON 路径列表；不传则使用内置公开样本。",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="报告输出目录，默认优先使用 reports/asr，写失败时自动回退到临时目录。",
    )
    parser.add_argument(
        "--skip-prepare",
        action="store_true",
        help="跳过公开样本下载与裁剪准备。",
    )
    return parser.parse_args()


def pick_writable_dir(preferred: str | Path, fallback_name: str) -> Path:
    """
    pick_writable_dir 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param preferred: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param fallback_name: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises RuntimeError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
    """
    for candidate in (Path(preferred).resolve(), Path(tempfile.gettempdir()) / fallback_name):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception:
            continue
    raise RuntimeError("无法找到可写的输出目录。")


def normalize_text(text: str) -> str:
    """
    normalize_text 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param text: 待处理文本；通常来自题干、转写或导入文档，需保留原始语义以便复核。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return "".join(
        ch for ch in text.lower().strip() if ch.isalnum() or "\u4e00" <= ch <= "\u9fff"
    )


def levenshtein(a: str, b: str) -> int:
    """
    levenshtein 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param a: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param b: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            insert_cost = curr[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (ca != cb)
            curr.append(min(insert_cost, delete_cost, replace_cost))
        prev = curr
    return prev[-1]


def cer(pred: str, gold: str) -> float:
    """
    cer 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param pred: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param gold: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    pred_norm = normalize_text(pred)
    gold_norm = normalize_text(gold)
    if not gold_norm:
        return 0.0 if not pred_norm else 1.0
    return levenshtein(pred_norm, gold_norm) / len(gold_norm)


def load_samples(sample_paths: list[str] | None) -> list[dict[str, object]]:
    """
    load_samples 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param sample_paths: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    if not sample_paths:
        return DEFAULT_SAMPLE_SET
    samples: list[dict[str, object]] = []
    for path in sample_paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        samples.extend(data)
    return samples


def download_file(url: str, target: Path) -> None:
    """
    download_file 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param url: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param target: 定向备面目标；承载考试体系、地区和岗位组合，不能只靠关键词推断。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, target)


def maybe_copy_funasr_examples(samples: list[dict[str, object]]) -> bool:
    """
    maybe_copy_funasr_examples 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param samples: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    cache_dir = os.environ.get("MODELSCOPE_CACHE")
    if not cache_dir:
        return False

    cache_root = Path(cache_dir)
    asr_source = next(cache_root.rglob("asr_example.wav"), None)
    vad_source = next(cache_root.rglob("vad_example.wav"), None)
    if asr_source is None or vad_source is None:
        return False

    for sample in samples:
        target = Path(str(sample["path"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        if sample["name"] == "asr_example":
            source = asr_source
        else:
            source = vad_source
        if source.exists() and not target.exists():
            shutil.copy2(source, target)
    return all(Path(str(sample["path"])).exists() for sample in samples if sample["name"] != "vad_example_clip")


def build_samples_from_local_examples(samples: list[dict[str, object]]) -> bool:
    """
    build_samples_from_local_examples 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param samples: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    cache_dir = os.environ.get("MODELSCOPE_CACHE")
    if not cache_dir:
        return False

    cache_root = Path(cache_dir)
    asr_source = next(cache_root.rglob("asr_example.wav"), None)
    vad_source = next(cache_root.rglob("vad_example.wav"), None)
    if asr_source is None or vad_source is None:
        return False

    for sample in samples:
        if sample["name"] == "asr_example":
            sample["path"] = str(asr_source)
        elif sample["name"] == "vad_example":
            sample["path"] = str(vad_source)
        elif sample["name"] == "vad_example_clip":
            sample["source_path"] = str(vad_source)
            sample["path"] = str(Path(tempfile.gettempdir()) / "kaogong_ai_asr_samples" / "vad_example_clip.wav")
    return True


def create_clip(sample: dict[str, object]) -> None:
    """
    create_clip 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param sample: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    source_path = Path(str(sample["source_path"]))
    target_path = Path(str(sample["path"]))
    if target_path.exists():
        return

    padded_source = target_path.with_name("vad_example_padded.wav")
    if not padded_source.exists():
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=16000:cl=mono",
                "-i",
                str(source_path),
                "-filter_complex",
                "[0:a][1:a]concat=n=2:v=0:a=1",
                str(padded_source),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(sample["clip_start"]),
            "-t",
            str(sample["clip_duration"]),
            "-i",
            str(padded_source),
            str(target_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def prepare_samples(samples: list[dict[str, object]]) -> None:
    """
    prepare_samples 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param samples: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    if not build_samples_from_local_examples(samples):
        writable_asset_dir = pick_writable_dir(ASSET_DIR, "kaogong_ai_asr_samples")
        for sample in samples:
            sample["path"] = str(writable_asset_dir / Path(str(sample["path"])).name)
            if sample.get("source_path"):
                sample["source_path"] = str(writable_asset_dir / Path(str(sample["source_path"])).name)

    copied = maybe_copy_funasr_examples(samples)
    if not copied:
        try:
            get_transcriber("funasr")
        except Exception:
            pass
        copied = maybe_copy_funasr_examples(samples)

    for sample in samples:
        path = Path(str(sample["path"]))
        url = sample.get("url")
        if url and not path.exists() and not copied:
            download_file(str(url), path)

    for sample in samples:
        if sample.get("source_path"):
            create_clip(sample)


def run_provider(provider: str, samples: list[dict[str, object]]) -> list[ASRRow]:
    """
    run_provider 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param provider: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param samples: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    transcriber = get_transcriber(provider)
    rows: list[ASRRow] = []

    if samples:
        try:
            transcriber.transcribe(str(Path(str(samples[0]["path"])).resolve()))
        except Exception:
            pass

    for sample in samples:
        audio_path = Path(str(sample["path"])).resolve()
        started = time.perf_counter()
        try:
            text = transcriber.transcribe(str(audio_path))
            elapsed = time.perf_counter() - started
            rows.append(
                ASRRow(
                    sample_name=str(sample["name"]),
                    provider=provider,
                    audio_path=str(audio_path),
                    raw_text=text,
                    normalized_text=normalize_text(text),
                    gold_text=str(sample["gold"]),
                    normalized_gold_text=normalize_text(str(sample["gold"])),
                    cer=cer(text, str(sample["gold"])),
                    elapsed_seconds=elapsed,
                )
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            rows.append(
                ASRRow(
                    sample_name=str(sample["name"]),
                    provider=provider,
                    audio_path=str(audio_path),
                    raw_text="",
                    normalized_text="",
                    gold_text=str(sample["gold"]),
                    normalized_gold_text=normalize_text(str(sample["gold"])),
                    cer=1.0,
                    elapsed_seconds=elapsed,
                    error=str(exc),
                )
            )
    return rows


def summarize(rows: list[ASRRow], provider: str) -> dict[str, float]:
    """
    summarize 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param rows: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param provider: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    provider_rows = [row for row in rows if row.provider == provider]
    if not provider_rows:
        return {"avg_cer": 1.0, "avg_seconds": 0.0}
    return {
        "avg_cer": round(mean(row.cer for row in provider_rows), 4),
        "avg_seconds": round(mean(row.elapsed_seconds for row in provider_rows), 4),
    }


def choose_winner(rows: list[ASRRow]) -> str:
    """
    choose_winner 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param rows: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    whisper = summarize(rows, "whisper")
    funasr = summarize(rows, "funasr")
    if funasr["avg_cer"] < whisper["avg_cer"]:
        return "FunASR"
    if funasr["avg_cer"] > whisper["avg_cer"]:
        return "Whisper"
    if funasr["avg_seconds"] < whisper["avg_seconds"]:
        return "FunASR"
    if funasr["avg_seconds"] > whisper["avg_seconds"]:
        return "Whisper"
    return "Tie"


def render_markdown(rows: list[ASRRow], generated_at: str) -> str:
    """
    render_markdown 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param rows: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param generated_at: 时间边界值；用于保持统计、计费或展示口径一致，需注意时区约定。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    whisper = summarize(rows, "whisper")
    funasr = summarize(rows, "funasr")
    winner = choose_winner(rows)
    lines = [
        "# ASR 基准报告",
        "",
        f"- 生成时间: `{generated_at}`",
        f"- 最终结论: `{winner}`",
        f"- Whisper 平均 CER: `{whisper['avg_cer']}`，平均耗时: `{whisper['avg_seconds']}` 秒",
        f"- FunASR 平均 CER: `{funasr['avg_cer']}`，平均耗时: `{funasr['avg_seconds']}` 秒",
        "",
        "| sample | provider | CER | seconds | text | error |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.sample_name} | {row.provider} | {row.cer:.3f} | {row.elapsed_seconds:.2f} | "
            f"{row.raw_text[:60]} | {row.error[:60]} |"
        )
    return "\n".join(lines)


def main() -> int:
    """
    main 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    args = parse_args()
    samples = load_samples(args.samples)
    if not args.skip_prepare:
        prepare_samples(samples)

    output_dir = pick_writable_dir(args.output_dir, "kaogong_ai_asr_reports")
    rows: list[ASRRow] = []
    for provider in ("whisper", "funasr"):
        rows.extend(run_provider(provider, samples))

    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"asr_benchmark_{generated_at}.json"
    md_path = output_dir / f"asr_benchmark_{generated_at}.md"

    payload = {
        "generated_at": generated_at,
        "summary": {
            "total": len(rows),
            "winner": choose_winner(rows),
            "whisper": summarize(rows, "whisper"),
            "funasr": summarize(rows, "funasr"),
        },
        "rows": [asdict(row) for row in rows],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(rows, generated_at), encoding="utf-8")
    print(json_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
