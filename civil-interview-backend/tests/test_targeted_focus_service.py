from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Question
from app.services.question_service import _normalize_keywords
from app.services.targeted_focus_service import (
    build_focus_analysis_from_questions,
    get_focus_analysis,
    get_or_create_focus_config,
    update_focus_config,
)


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)()


def test_focus_analysis_returns_empty_for_missing_bank_data():
    engine, db = _session()
    try:
        result = build_focus_analysis_from_questions(db, "shanghai", "general")
        assert result["questionCount"] == 0
        assert result["coreFocus"] == []
        assert result["message"] == "暂无足够题库数据"
    finally:
        db.close()
        engine.dispose()


def test_focus_analysis_uses_real_question_bank_statistics():
    engine, db = _session()
    try:
        db.add(
            Question(
                id="js_focus_1",
                stem="江苏基层综合管理岗如何提升群众服务？",
                dimension="analysis",
                province="jiangsu",
                scoring_points=[
                    {"content": "基层治理", "score": 10},
                    {"content": "群众服务", "score": 10},
                    {"content": "闭环落实", "score": 10},
                ],
                keywords=_normalize_keywords(
                    {"scoring": ["基层治理", "群众服务"], "deducting": [], "bonus": []},
                    {"source": "manual", "positionTags": ["jiangsu_a"], "tags": ["基层治理", "群众服务"]},
                ),
            )
        )
        db.commit()

        result = build_focus_analysis_from_questions(db, "jiangsu", "jiangsu_a")

        assert result["questionCount"] == 1
        assert result["coreFocus"][0]["name"] == "综合分析"
        assert "基层治理" in result["hotTopics"]
    finally:
        db.close()
        engine.dispose()


def test_manual_focus_config_overrides_public_focus_result():
    engine, db = _session()
    try:
        db.add(
            Question(
                id="js_focus_2",
                stem="江苏综合管理岗如何推进工作落实？",
                dimension="practical",
                province="jiangsu",
                scoring_points=[{"content": "工作落实", "score": 10}],
                keywords=_normalize_keywords(
                    {"scoring": ["工作落实"], "deducting": [], "bonus": []},
                    {"source": "manual", "positionTags": ["jiangsu_a"]},
                ),
            )
        )
        db.commit()
        config = get_or_create_focus_config(db, "jiangsu", "jiangsu_a")

        update_focus_config(
            db,
            config.id,
            published_result={
                **config.auto_result,
                "coreFocus": [{"name": "管理员重点", "weight": 88, "desc": "手动发布"}],
            },
            publish_mode="manual",
            is_active=True,
            username="admin",
        )
        result = get_focus_analysis(db, "jiangsu", "jiangsu_a")

        assert result["dataSource"] == "admin_manual"
        assert result["coreFocus"][0]["name"] == "管理员重点"
    finally:
        db.close()
        engine.dispose()
