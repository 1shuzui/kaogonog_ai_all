from copy import deepcopy
from types import SimpleNamespace
from app.services.score_summary import normalized_dimensions, summarize_answers


def answer(id, **score):
    return SimpleNamespace(question_id=id, score_result=score)


def test_different_point_scales_are_normalized_before_history_display():
    result = summarize_answers([answer('a', totalScore=28.8, maxScore=36), answer('b', totalScore=80, maxScore=100)])
    assert result['totalScore'] == 80 and result['maxScore'] == 100
    legacy = summarize_answers([answer('a', totalScore=80, maxScore=100, questionScore=16, questionMaxScore=20),
                                answer('b', totalScore=60, maxScore=100, questionScore=48, questionMaxScore=80)])
    assert legacy['totalScore'] == 64 and legacy['possiblePoints'] == 100


def test_suite_appearance_counts_once_and_actual_replaces_default():
    shared = dict(maxScore=36, appearanceScore=5, appearanceScoreMax=5, appearanceScoreScope='suite', appearanceScoreSource='profile_default')
    questions = {id: SimpleNamespace(keywords={'_meta': {'suiteKey': 'same-suite'}}) for id in ['a', 'b']}
    results = [answer('a', totalScore=29.8, contentScore=24.8, **shared), answer('b', totalScore=29.8, contentScore=24.8, **shared)]
    summary = summarize_answers(results, questions)
    assert summary['earnedPoints'] == 54.6 and summary['possiblePoints'] == 67
    assert summary['totalScore'] == round(54.6 / 67 * 100, 2)
    results[1].score_result.update(appearanceScore=3, appearanceScoreSource='actual', totalScore=27.8)
    assert summarize_answers(results, questions)['earnedPoints'] == 52.6


def test_ability_dimensions_keep_a_consistent_scale_without_mutating_saved_json():
    old = dict(contentScore=24.8, appearanceScore=5, appearanceScoreMax=5, maxScore=36,
               dimensions=[{'name': '综合分析', 'score': 4.96, 'maxScore': 20}, {'name': '实务落地', 'score': 19.84, 'maxScore': 80}])
    original = deepcopy(old)
    normalized = normalized_dimensions(old)
    assert normalized[0]['score'] == 16
    assert old == original
    assert normalized_dimensions({**old, 'dimensions': normalized}) == normalized


def test_summary_averages_all_answers_not_just_the_last_answer_and_ignores_pending():
    first = answer('a', totalScore=50, maxScore=100, dimensions=[{'name': '综合分析', 'score': 10, 'maxScore': 20}])
    second = answer('b', totalScore=90, maxScore=100, dimensions=[{'name': '综合分析', 'score': 18, 'maxScore': 20}])
    summary = summarize_answers([first, second, answer('pending', mediaRecord={'fileUrl': 'stored'}), answer('pending-null', totalScore=None)])
    assert summary['questionCount'] == 2
    assert summary['dimensions'][0]['score'] == 14
    assert summary['totalScore'] == 70
