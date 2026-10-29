"""Exam units and explicit direction filters, independent of source classification."""
import re

MEDICAL_PORTALS = {"医疗卫生面试", "医疗系统考试", "医疗卫生考试"}


def values(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item for item in re.split(r"[、，,；;/\s]+", str(value or "")) if item]


def exam_track(meta):
    # Use source labels, never incidental medical vocabulary in a question stem.
    portals = set(values(meta.get("portalTags")) + values(meta.get("displayPortals")))
    if (portals & MEDICAL_PORTALS or meta.get("examCategory") in MEDICAL_PORTALS
            or meta.get("examTrack") == "medical"):
        return "medical"
    source = " ".join(str(meta.get(key) or "") for key in
                      ("sourceTitleRaw", "suiteName", "sourceDocument", "system", "positionType"))
    if any(label in source for label in ("医疗", "卫健", "医院", "疾控", "医师", "护理岗", "卫生系统")):
        return "medical"
    # Legacy importers inferred positionTags from the stem. A hospital mentioned
    # in a general public-institution question must not change the exam unit.
    if meta.get("examCategory") == "事业单位考试" and "事业单位" in source:
        return "institution"
    if "medical" in values(meta.get("positionTags")):
        return "medical"
    return "institution" if meta.get("examCategory") == "事业单位考试" else ""



def matches_scope(meta, filters):
    track = str(filters.get("examTrack") or "").strip()
    if track and exam_track(meta) != track:
        return False
    portal = filters.get("portalTag") or filters.get("displayPortal")
    if portal and portal not in values(meta.get("portalTags")) + values(meta.get("displayPortals")):
        return False
    for key in ("examSubcategory", "system"):
        expected = str(filters.get(key) or "").strip()
        if expected and expected != str(meta.get(key) or "").strip():
            return False
    # Older importers extracted city/district from question prose. Prefer the
    # original suite heading; all questions in that source share its location.
    title = str(meta.get("sourceTitleRaw") or meta.get("suiteName") or "").strip()
    heading = re.split(r"事业单位|面试|招聘|真题", title, maxsplit=1)[0]
    city = str(filters.get("city") or "").strip().removesuffix("市")
    districts = [re.sub(r"[县区市]$", "", item) for item in values(filters.get("district"))]
    if city:
        if "江苏" in heading or city in heading:
            if city not in heading:
                return False
        else:
            places = [str(meta.get(key) or "").strip() for key in ("city", "subcategory")]
            if not any(place.removeprefix("江苏省").startswith(city) for place in places):
                return False
    if districts:
        location = heading if "江苏" in heading else " ".join(str(meta.get(key) or "") for key in ("district", "subcategory2", "subcategory"))
        if not any(district in location for district in districts):
            return False
    if filters.get("areaLevel") == "provincial":
        # Province-wide joint exams are not necessarily provincial institution jobs.
        if not (re.search(r"省属|省级|江苏省[^省市县区]{1,12}(?:厅|局|委员会)", title)
                or meta.get("areaLevel") == "provincial"):
            return False
    expected_positions = []
    for key in ("positionType", "positionTag", "positionTags"):
        expected_positions += values(filters.get(key))
    if expected_positions:
        actual = set(values(meta.get("positionTags")) + [str(meta.get("positionType") or ""), str(meta.get("position") or "")])
        if not actual.intersection(expected_positions):
            return False
    return True
