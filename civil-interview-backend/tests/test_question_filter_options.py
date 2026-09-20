"""Filter facets use real metadata without changing bank queries or access rules."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.routes.question_routes import router
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.entities import Question
from app.schemas.common import AuthUser
from app.services import question_service


BASE_FILTERS = {
    "province": "jiangsu",
    "examCategory": "事业单位考试",
    "dimension": "analysis",
}


def question(id_, *, province="jiangsu", dimension="analysis", stem="群众沟通", **meta):
    return Question(
        id=id_, province=province, dimension=dimension, stem=stem,
        scoring_points=[{"content": "PRIVATE_SCORING", "score": 10}],
        keywords={"scoring": ["PRIVATE_KEYWORD"], "_meta": {
            "examCategory": "事业单位考试",
            "sourceDocument": "PRIVATE_SOURCE_仅来源.docx",
            "referenceAnswer": "PRIVATE_ANSWER",
            **meta,
        }},
    )


@pytest.fixture
def db():
    # Isolated in-memory fixtures, never the configured application database.
    engine = create_engine(
        "sqlite:///:memory:", poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Question.__table__.create(engine)
    with Session(engine, autoflush=False) as session:
        session.add_all([
            question("old", year=["2016"], subcategory="盐城市", subcategory2="东台", positionTags=["medical"]),
            question("new", examDate="2026-06-01", year=["2015"], suiteName="2001旧标题",
                     subcategory="盐城市", subcategory2="东台", positionTags=["medical"]),
            question("unknown", stem="群众讨论2027规划", subcategory="盐城市", subcategory2="盐都", positionTags=["general"]),
            question("sibling", year="2024", subcategory="淮安市", subcategory2="清江浦", positionTags=["tax"]),
            question("lookalike", year="2018", subcategory="盐城", subcategory2="东台乡", positionTags=["general"]),
            question("blank", year="未知", subcategory=" \t ", subcategory2=" ", positionTags=["general"]),
            question("anhui", province="anhui", year="2022", subcategory="合肥市", subcategory2="市直"),
            question("national", province="national", year="2020", subcategory="通用"),
            question("other-category", examCategory="事业单位考试（专项）", year="2023", subcategory="专项"),
            question("other-dimension", dimension="emergency", year="2019", subcategory="盐城市", subcategory2="东台"),
        ])
        session.commit()
        session.expunge_all()
        yield session
    engine.dispose()


@pytest.fixture
def app(db):
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_db] = lambda: db
    application.dependency_overrides[get_current_user] = lambda: AuthUser(
        username="paid-fixture", permissions={"canAccessPremiumModules": True},
    )
    return application


def facets(db, **filters):
    return question_service.get_question_filter_options(db, **filters)


def test_filter_options_is_a_static_authorized_route(app):
    with TestClient(app) as client:
        response = client.get("/questions/filter-options", params=BASE_FILTERS)
    assert response.status_code == 200
    assert response.json() == {
        "options": {
            "year": ["2026", "2024", "2018", "2016"],
            "subcategory": sorted(["盐城市", "淮安市", "盐城"]),
            "subcategory2": sorted(["东台", "盐都", "清江浦", "东台乡"]),
        },
        "unclassifiedYearCount": 2,
        "questionCount": 6,
    }


def test_years_are_real_sorted_and_include_unknown_in_count(db):
    result = facets(db, **BASE_FILTERS)
    assert result["options"]["year"] == ["2026", "2024", "2018", "2016"]
    assert result["unclassifiedYearCount"] == 2
    assert result["questionCount"] == 6


@pytest.mark.parametrize("year", ["2016", "2026", "1900", "2016,2026", "invalid"])
def test_selected_year_never_restricts_facets_or_counts(db, year):
    assert facets(db, **BASE_FILTERS, year=year) == facets(db, **BASE_FILTERS)


def test_cascades_exclude_their_own_and_descendant_filters(db):
    result = facets(db, **BASE_FILTERS, subcategory="盐城市", subcategory2="东台", year="2016")
    assert result == {
        "options": {
            "year": ["2026", "2016"],
            "subcategory": sorted(["盐城市", "淮安市", "盐城"]),
            "subcategory2": sorted(["东台", "盐都"]),
        },
        "unclassifiedYearCount": 0,
        "questionCount": 2,
    }
    parent = facets(db, **BASE_FILTERS, subcategory="盐城市")
    assert parent["questionCount"] == 3
    assert parent["unclassifiedYearCount"] == 1
    cleared = facets(db, **BASE_FILTERS, subcategory="", subcategory2="")
    assert cleared["questionCount"] == 6
    assert "清江浦" in cleared["options"]["subcategory2"]


@pytest.mark.parametrize("field,value", [
    ("examCategory", "事业单位"),
    ("subcategory", "盐"),
    ("subcategory2", "东"),
])
def test_classification_matches_are_exact(db, field, value):
    result = facets(db, **{**BASE_FILTERS, field: value})
    assert result["questionCount"] == 0
    assert result["options"]["year"] == []
    assert result["unclassifiedYearCount"] == 0


def test_empty_and_all_province_do_not_mean_national(db):
    common = {"examCategory": "事业单位考试", "dimension": "analysis"}
    assert facets(db, **common, province="") == facets(db, **common, province="all")
    assert facets(db, **common, province="all")["questionCount"] == 8
    national = facets(db, **common, province="national")
    assert national["questionCount"] == 1
    assert national["options"]["year"] == ["2020"]
    assert facets(db, **common, province="missing")["questionCount"] == 0


def test_keyword_only_searches_stem_and_dimension_is_exact(db):
    assert facets(db, **BASE_FILTERS, keyword="仅来源")["questionCount"] == 0
    unknown = facets(db, **BASE_FILTERS, keyword="2027")
    assert unknown["questionCount"] == unknown["unclassifiedYearCount"] == 1
    assert unknown["options"]["year"] == []
    result = facets(db, **{**BASE_FILTERS, "dimension": "emergency"})
    assert result["options"]["year"] == ["2019"]


@pytest.mark.parametrize("position,expected_years,count,unknown", [
    ("medical", ["2026", "2016"], 2, 0),
    ("tax", ["2024"], 1, 0),
    ("general", ["2018"], 3, 2),
    ("jiangsu_a", [], 0, 0),
])
def test_positions_reuse_bank_matching(db, position, expected_years, count, unknown):
    result = facets(db, **BASE_FILTERS, position=position)
    assert result["options"]["year"] == expected_years
    assert result["questionCount"] == count
    assert result["unclassifiedYearCount"] == unknown


def test_position_alias_can_match_stem_without_explicit_tags(db):
    db.add(question("stem-alias", stem="群众税务服务", year="2028"))
    db.commit()
    result = facets(db, **BASE_FILTERS, position="tax")
    assert result["options"]["year"] == ["2028", "2024"]
    assert result["questionCount"] == 2


def test_year_source_fallbacks_and_raw_category_values(db):
    db.add_all([
        question("suite", suiteName="2014年真题", subcategory=" 原样分类 "),
        question("source-id", sourceQuestionId="Q2013-01"),
        question("document", sourceDocument="2012年真题.docx"),
        question("multiple", year=["2011", "2010", "2011"]),
    ])
    db.commit()
    result = facets(db, **BASE_FILTERS)
    assert result["options"]["year"] == ["2026", "2024", "2018", "2016", "2014", "2013", "2012", "2011", "2010"]
    assert " 原样分类 " in result["options"]["subcategory"]
    assert " \t " not in result["options"]["subcategory"]


def test_missing_metadata_and_non_string_categories_do_not_create_options(db):
    db.add_all([
        Question(id="no-meta", province="blank-fixture", stem="metadata absent", keywords=None),
        question("invalid-categories", province="blank-fixture", subcategory=["not-a-query-value"], subcategory2=123),
    ])
    db.commit()
    result = facets(db, province="blank-fixture")
    assert result == {
        "options": {"year": [], "subcategory": [], "subcategory2": []},
        "unclassifiedYearCount": 2,
        "questionCount": 2,
    }


@pytest.mark.parametrize("position", ["", "medical", "tax"])
def test_only_one_minimal_select_no_serialization_ai_cache_or_writes(db, monkeypatch, position):
    def forbidden(*args, **kwargs):
        pytest.fail("Filter options must not serialize questions, write, generate, or cache")

    for name in ("_q_to_dict", "call_llm_api_async", "sync_curated_question_assets", "_get_cached_list", "_set_cached_list"):
        monkeypatch.setattr(question_service, name, forbidden)
    monkeypatch.setattr(db, "commit", forbidden)
    monkeypatch.setattr(db, "flush", forbidden)
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        result = facets(db, **BASE_FILTERS, position=position)
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert len(statements) == 1
    select = statements[0].split("FROM", 1)[0].lower()
    assert select.lstrip().startswith("select")
    assert "keywords" in select
    for column in ("scoring_points", "prep_time", "answer_time", "dimension", "province"):
        assert column not in select
    assert ("stem" in select) == bool(position)
    assert " limit " not in statements[0].lower()
    assert set(result) == {"options", "unclassifiedYearCount", "questionCount"}
    assert "PRIVATE_" not in json.dumps(result)


def test_missing_login_cannot_read_facets(app, db, monkeypatch):
    app.dependency_overrides.pop(get_current_user)
    monkeypatch.setattr(db, "query", lambda *args: pytest.fail("Anonymous request must not query metadata"))
    with TestClient(app) as client:
        response = client.get("/questions/filter-options")
    assert response.status_code == 401
    assert "options" not in response.json()


def test_unpaid_user_cannot_read_facets(app, db, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: AuthUser(username="unpaid-fixture")
    monkeypatch.setattr(db, "query", lambda *args: pytest.fail("Unpaid request must not query metadata"))
    with TestClient(app) as client:
        response = client.get("/questions/filter-options")
    assert response.status_code == 403
    assert "options" not in response.json()


def test_admin_retains_existing_access(app):
    app.dependency_overrides[get_current_user] = lambda: AuthUser(username="admin-fixture", isAdmin=True)
    with TestClient(app) as client:
        response = client.get("/questions/filter-options", params=BASE_FILTERS)
    assert response.status_code == 200
    assert response.json()["questionCount"] == 6


def test_http_passes_parent_and_position_filters_but_ignores_year(app):
    with TestClient(app) as client:
        response = client.get("/questions/filter-options", params={
            **BASE_FILTERS, "keyword": "群众", "position": "medical",
            "subcategory": "盐城市", "subcategory2": "东台", "year": "1900",
        })
    assert response.status_code == 200
    assert response.json() == {
        "options": {"year": ["2026", "2016"], "subcategory": ["盐城市"], "subcategory2": ["东台"]},
        "unclassifiedYearCount": 0,
        "questionCount": 2,
    }


def test_openapi_has_typed_minimal_response_and_existing_filter_parameters(app):
    spec = app.openapi()
    operation = spec["paths"]["/questions/filter-options"]["get"]
    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "keyword", "dimension", "province", "position", "examCategory", "subcategory", "subcategory2", "year",
    }
    assert operation["security"]
    response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    response_schema = spec["components"]["schemas"][response_ref.rsplit("/", 1)[-1]]
    assert set(response_schema["properties"]) == {"options", "unclassifiedYearCount", "questionCount"}
    assert set(response_schema["required"]) == set(response_schema["properties"])
