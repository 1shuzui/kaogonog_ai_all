#!/usr/bin/env python3
"""
这个脚本从 docx 文档里抽取纯文本，主要给题库导入前的排查使用，方便先看原文结构有没有丢。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from xml.etree import ElementTree


WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_docx_text(input_path: str | Path) -> str:
    """
    读取 .docx 中的段落文本，并按行拼接。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param input_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    docx_path = Path(input_path)
    with zipfile.ZipFile(docx_path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))

    lines: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        parts = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE)]
        line = "".join(parts).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def default_output_path(input_path: str | Path) -> Path:
    """
    为输入文档生成默认输出路径。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param input_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    docx_path = Path(input_path)
    return docx_path.with_suffix(".extracted.txt")


def write_extracted_text(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    """
    提取并写出文本文件。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param input_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param output_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    resolved_output = Path(output_path) if output_path is not None else default_output_path(input_path)
    resolved_output.write_text(extract_docx_text(input_path), encoding="utf-8")
    return resolved_output


def build_argument_parser() -> argparse.ArgumentParser:
    """
    构建 CLI 参数解析器。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    parser = argparse.ArgumentParser(description="从 .docx 提取纯文本。")
    parser.add_argument("input_docx", help="输入 .docx 文件路径")
    parser.add_argument("output_txt", nargs="?", help="输出 .extracted.txt 路径")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    CLI 入口。

    脚本模块服务于题库处理、ASR 评测和回归验证，注释用于保留数据来源与执行风险。

    @param argv: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    args = build_argument_parser().parse_args(argv)
    output_path = write_extracted_text(args.input_docx, args.output_txt)
    print(f"已生成提取文本: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
