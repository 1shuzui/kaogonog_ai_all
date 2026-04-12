"""大模型调用客户端。

这个模块的目标不是“功能多”，而是“稳定”：
1. 统一封装模型调用入口
2. 给模型增加 JSON 输出约束
3. 做失败重试
4. 尽量从不规范输出中提取出 JSON

对弱基础同学来说，最重要的一点是：
模型返回的内容不一定可靠，所以这里必须做兜底。
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from app.core.config import settings
from app.models.schemas import LLMGenerationResult

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = (
    "你是一个严格的结构化评分引擎。"
    "只输出合法 JSON 对象，不要输出 Markdown、解释或多余文本。"
)


class LLMClient:
    """大模型客户端。

    这里使用“保守策略”：
    - temperature 低一点，减少发散
    - 尽量要求 JSON-only 输出
    - 失败时自动重试
    """

    def __init__(self):
        # 把配置读进来，避免在业务方法里到处引用 settings。
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model_name = settings.LLM_MODEL_NAME
        self.max_retries = settings.LLM_MAX_RETRIES
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        self.client = self._build_client()

    def _build_client(self):
        """真正初始化 OpenAI 兼容客户端。"""
        if not self.api_key:
            logger.warning("未配置 %s API 密钥，大模型调用将不可用。", self.provider)
            return None

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("缺少 openai 依赖，请先安装 requirements.txt。") from exc

        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def _extract_message_text(self, content: Any) -> str:
        """把 SDK 返回内容统一整理成字符串。

        有些模型 / SDK 版本返回字符串，
        有些会返回分段列表，所以这里做统一兼容。
        """
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for item in content:
                text = getattr(item, "text", None)
                if text:
                    parts.append(text)
                    continue
                if isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
            return "".join(parts).strip()
        return str(content).strip()

    def _extract_json_candidate(self, content: str) -> str:
        """尽量从模型输出中截出 JSON 对象。

        为什么需要这个函数？
        因为很多模型即使你要求“只返回 JSON”，
        也可能偷偷包一层 ```json ... ``` 或加一句解释。

        这里的策略是：
        1. 如果发现 Markdown 代码块，就取最外层大括号之间内容
        2. 否则从第一个 { 开始，按大括号配对截出完整 JSON
        """
        if "```" in content:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return content[start : end + 1].strip()

        start = content.find("{")
        if start == -1:
            return content.strip()

        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(content)):
            char = content[index]
            if char == "\\" and in_string:
                # 字符串里的转义字符需要特殊处理，否则容易误判引号。
                escape = not escape
                continue
            if char == '"' and not escape:
                in_string = not in_string
            escape = False

            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return content[start : index + 1].strip()

        return content.strip()

    def _safe_parse_json(self, content: str) -> Optional[Dict[str, Any]]:
        """安全解析 JSON。

        如果解析失败，不直接抛异常，而是返回 None，
        这样上层可以决定是否重试。
        """
        candidate = self._extract_json_candidate(content)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    def _request_completion(self, messages: list[dict[str, str]]):
        """向模型发起一次真正的请求。"""
        if not self.client:
            raise RuntimeError("LLM 客户端未初始化，请检查 API 密钥和依赖。")

        request_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
        }
        if settings.LLM_FORCE_JSON_RESPONSE:
            # 某些 OpenAI 兼容接口支持 response_format=json_object。
            # 如果支持，能明显减少模型乱输出的概率。
            request_kwargs["response_format"] = {"type": "json_object"}

        try:
            return self.client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            if "response_format" in request_kwargs:
                # 不是所有兼容服务都支持 response_format。
                # 如果不支持，就退回普通调用，而不是直接失败。
                logger.warning("JSON response_format 不可用，回退到普通模式: %s", exc)
                request_kwargs.pop("response_format", None)
                return self.client.chat.completions.create(**request_kwargs)
            raise

    def generate(
        self,
        prompt: str,
        system_message: str | None = None,
    ) -> Optional[LLMGenerationResult]:
        """生成结构化评分结果。

        这里的完整策略是：
        1. 先按严格 JSON 模式请求
        2. 如果模型输出不合法，保留原输出
        3. 下一轮把“上一轮不合法”告诉模型，让它自我修复
        4. 多次失败后返回 None，由上层决定怎么报错
        """

        last_content = ""
        base_messages = [
            {"role": "system", "content": system_message or SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ]

        for attempt in range(self.max_retries):
            messages = list(base_messages)
            if last_content:
                # 如果上一轮 JSON 不合法，就把上一轮原文回传给模型，让它修复格式。
                messages.extend(
                    [
                        {"role": "assistant", "content": last_content},
                        {
                            "role": "user",
                            "content": (
                                "上一个输出未通过 JSON 校验。"
                                "请修复为合法 JSON，并继续只返回 JSON 对象。"
                            ),
                        },
                    ]
                )

            try:
                response = self._request_completion(messages)
                content = self._extract_message_text(response.choices[0].message.content)
                last_content = content
                result = self._safe_parse_json(content)

                if result is not None:
                    # 一旦解析成功，立刻返回。
                    return LLMGenerationResult(
                        raw_content=content,
                        parsed_payload=result,
                    )

                logger.warning(
                    "JSON 解析失败，正在重试 (%s/%s)，原始输出片段: %s",
                    attempt + 1,
                    self.max_retries,
                    content[:300],
                )
            except Exception as exc:
                logger.error(
                    "LLM 调用异常 (%s/%s): %s",
                    attempt + 1,
                    self.max_retries,
                    exc,
                )

            # 指数退避：第 1 次等 1 秒，第 2 次等 2 秒，第 3 次等 4 秒……
            # 可以减少短时间连续重试对接口的冲击。
            time.sleep(2**attempt)

        logger.error("LLM API 多次重试仍失败，已放弃本次请求。")
        return None
