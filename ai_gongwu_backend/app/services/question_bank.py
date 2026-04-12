"""题库服务。

这个模块解决两个问题：
1. 启动时如何把题库 JSON 正确读进来
2. 运行时如何根据 question_id 找到对应题目

把题库逻辑单独抽出来后，后续如果你想：
- 从单题 JSON 升级成多题 JSON
- 从本地文件升级成数据库
- 增加题目版本管理
都可以在这里平滑扩展。
"""

import logging
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Tuple

from pydantic import ValidationError

from app.core.config import settings
from app.models.schemas import QuestionDefinition
from app.utils.data_loader import load_json_data

logger = logging.getLogger(__name__)


class QuestionNotFoundError(ValueError):
    """请求的题目 ID 不存在时抛出的异常。"""


class QuestionBank:
    """基于 JSON 文件的内存题库。

    “内存题库” 的意思是：
    程序启动后先读一次文件，之后都从内存查，不再反复读磁盘。
    """

    def __init__(self, source_path: str | Path):
        # resolve_path 会把相对路径转成稳定路径，减少启动目录不同造成的问题。
        self.source_path = settings.resolve_path(source_path)
        self._questions = self._load_questions()

    @property
    def count(self) -> int:
        """返回题库中的题目总数。"""

        return len(self._questions)

    def list_ids(self) -> List[str]:
        """返回所有题目的 ID 列表。"""

        return sorted(self._questions.keys())

    def list_questions(self) -> List[QuestionDefinition]:
        """返回按题目 ID 排序的题目列表。"""

        return [self._questions[question_id] for question_id in sorted(self._questions)]

    def get_question(self, question_id: str) -> QuestionDefinition:
        """根据 question_id 返回一条已经校验过结构的题目。"""

        if question_id not in self._questions:
            available_ids = ", ".join(self.list_ids()) or "无"
            raise QuestionNotFoundError(
                f"题目不存在: {question_id}。当前可用题目 ID: {available_ids}"
            )
        return self._questions[question_id]

    def _load_questions(self) -> Dict[str, QuestionDefinition]:
        questions: Dict[str, QuestionDefinition] = {}
        for raw_question, source_path in self._iter_question_sources():
            try:
                # 第三步：使用 Pydantic 做结构化校验，
                # 防止题库字段缺失、类型错误等问题悄悄溜进系统。
                question = QuestionDefinition.model_validate(raw_question)
            except ValidationError as exc:
                raise ValueError(f"题库数据结构非法: {source_path} -> {exc}") from exc

            if question.id in questions:
                # question_id 必须唯一，否则后面查询会产生歧义。
                raise ValueError(f"题库中存在重复的 question_id: {question.id}")
            questions[question.id] = question

        if not questions:
            raise ValueError(f"题库路径下未加载到任何题目: {self.source_path}")

        logger.info("题库加载完成: %s, 共 %s 题", self.source_path, len(questions))
        return questions

    def _iter_question_sources(self) -> Iterator[Tuple[object, Path]]:
        """统一遍历题库来源。

        兼容两种题库存储方式：
        1. 单个 JSON 文件
        2. 存放多份题目 JSON 的目录
        """

        if self.source_path.is_file():
            raw_data = load_json_data(self.source_path)
            for raw_question in self._coerce_to_question_list(raw_data):
                yield raw_question, self.source_path
            return

        if self.source_path.is_dir():
            json_files = sorted(self.source_path.rglob("*.json"))
            if not json_files:
                raise ValueError(f"题库目录下未找到任何 JSON 文件: {self.source_path}")
            for json_file in json_files:
                raw_data = load_json_data(json_file)
                for raw_question in self._coerce_to_question_list(raw_data):
                    yield raw_question, json_file
            return

        raise ValueError(f"题库路径不存在或不可读: {self.source_path}")

    @staticmethod
    def _coerce_to_question_list(raw_data: object) -> Iterable[object]:
        """把不同形态的 JSON 数据统一整理为“题目列表”。

        兼容以下几种写法：
        1. [题目1, 题目2, ...]
        2. {"questions": [题目1, 题目2, ...]}
        3. 单题对象 {"id": "...", ...}
        """
        if isinstance(raw_data, list):
            return raw_data
        if isinstance(raw_data, dict):
            questions = raw_data.get("questions")
            if isinstance(questions, list):
                return questions
            return [raw_data]
        raise ValueError("题库 JSON 必须是对象、对象列表，或包含 questions 数组的对象。")
