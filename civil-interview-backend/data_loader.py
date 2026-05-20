import json
import pandas as pd
import os


def load_question_json(filepath):
    """加载 JSON 格式的题目"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_question_excel(filepath, question_id=None):
    """
    从 Excel 题库加载题目
    如果提供了 question_id，返回特定题目；否则返回第一题作为示例
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    # 读取 question_bank 工作表
    df_questions = pd.read_excel(filepath, sheet_name='question_bank')
    # 读取 keyword_rules 工作表
    df_rules = pd.read_excel(filepath, sheet_name='keyword_rules')

    if question_id:
        df_questions = df_questions[df_questions['question_id'] == question_id]
        df_rules = df_rules[df_rules['question_id'] == question_id]

    if df_questions.empty:
        return None

    row = df_questions.iloc[0]

    # 构建题目对象
    question = {
        "question_id": row.get('question_id'),
        "province": row.get('province'),
        "type": row.get('question_type'),
        "question": row.get('question_text'),
        "fullScore": 30,  # 默认满分，可根据实际调整
        "dimensions": [],
        "scoringCriteria": [],
        "coreKeywords": [],
        "strongKeywords": [],
        "weakKeywords": [],
        "bonusKeywords": [],
        "penaltyKeywords": []
    }

    # 解析维度配置 JSON
    dim_config_str = row.get('dimension_config', '{}')
    try:
        dim_config = json.loads(dim_config_str)
        for dim_name, scores in dim_config.items():
            question["dimensions"].append({
                "name": dim_name,
                "score": scores.get('max', 0)
            })
            # 简单映射评分标准，实际项目中可细化
            question["scoringCriteria"].append(f"考察{dim_name}维度的表现")
    except json.JSONDecodeError:
        print("警告：维度配置 JSON 解析失败")

    # 解析关键词规则
    for _, rule_row in df_rules.iterrows():
        k_type = rule_row.get('keyword_type')
        k_words = str(rule_row.get('keyword', '')).split(',')
        k_synonyms = str(rule_row.get('synonyms', '')).split(',')
        all_words = [w.strip() for w in k_words + k_synonyms if w.strip()]

        if k_type == '采分':
            # 根据分值简单区分核心和强关联，这里简化处理全部放入 core 或 strong
            # 实际逻辑可根据 score_change 大小判断
            question["coreKeywords"].extend(all_words)
        elif k_type == '扣分':
            question["penaltyKeywords"].extend(all_words)
        elif k_type == '加分':
            question["bonusKeywords"].extend(all_words)

    # 去重
    for key in ['coreKeywords', 'strongKeywords', 'weakKeywords', 'bonusKeywords', 'penaltyKeywords']:
        question[key] = list(set(question[key]))

    return question


# 兼容旧版调用
def load_question(filepath):
    if filepath.endswith('.json'):
        return load_question_json(filepath)
    elif filepath.endswith('.xlsx'):
        return load_question_excel(filepath)
    else:
        # 默认尝试 JSON
        return load_question_json(filepath)


if __name__ == '__main__':
    # 测试加载
    try:
        q = load_question('question.json')
        print(f"加载成功：{q.get('question', '')[:50]}...")
    except Exception as e:
        print(f"加载失败：{e}")