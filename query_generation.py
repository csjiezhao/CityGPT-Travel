from config import HOTEL_MAP, CUISINE_MAP, CITY_MAP
from llm_api import LLMCaller

import argparse
import random
import time
import json
import pandas as pd
from datetime import datetime, timedelta

def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def estimate_budget(days, people, hotel_type=None):
    """根据天数、人数和酒店类型估算旅行预算（四舍五入到百位）"""
    base_per_person_per_day = 500  # 基础起点价格

    # 酒店类型影响因子
    hotel_factor_map = {
        "经济型": 1,
        "舒适型": 2,
        "高档型": 3,
        "奢华型": 4,
        "民宿客栈": 4,
        None: 1.5  # 没有指定酒店时默认1.0
    }

    factor = hotel_factor_map.get(hotel_type, 1.0)
    raw = base_per_person_per_day * days * people * factor

    return round(raw / 100) * 100


def generate_travel_query(city_name, llm, days, preference_count, difficulty):
    travel_date = random_date(datetime.today(), datetime.today() + timedelta(days=90)).strftime("%Y-%m-%d")
    people_number = random.randint(1, 3)

    if preference_count == 0:
        budget = estimate_budget(days, people_number)
        prompt = f"""请根据以下信息创建一个旅行者的查询（query）。
        - 旅行天数：{days} 天
        - 人数：{people_number} 人
        - 旅行开始日期：{travel_date}
        - 预算约束：预算为 {budget} 元。
        ### 要求
        1. 用真实用户的语气表达需求，使 query 自然、富有变化。
        2. 输出JSON结构，格式如下：
           {{
               "days": {days},
               "people_number": {people_number},
               "date": "{travel_date}",
               "preference_constraint": {{"budget": {budget}}},
               "query": "请你帮我规划一个{people_number}人的{city_name}旅行方案，时间从{travel_date}开始，为期{days}天，预算大约为：{budget}元。"
           }}"""

    elif preference_count == 1:
        extra_constraint = random.choice(["hotel", "cuisines"])
        if extra_constraint == "hotel":
            constraint_value = random.choice(list(HOTEL_MAP.keys()))
            budget = estimate_budget(days, people_number, hotel_type=constraint_value)
            preference_str = f"我希望住在{constraint_value}类型的酒店。"

            prompt = f"""请根据以下信息创建一个旅行者的查询（query），使用流畅的自然语言文本描述。
            - 旅行天数：{days} 天
            - 人数：{people_number} 人
            - 旅行开始日期：{travel_date}
            - 预算约束：预算为 {budget} 元
            - 住宿偏好：{preference_str}
            ### 要求
            1. 用真实用户的语气表达需求，使 query 自然、富有变化。
            2. 输出JSON结构，格式如下：
            {{
                "days": {days},
                "people_number": {people_number},
                "date": "{travel_date}",
                "preference_constraint": {{
                    "budget": {budget},
                    "hotel": "{constraint_value}"
                }},
                "query": "请你帮我规划一个{people_number}人的{city_name}旅行方案，时间从{travel_date}开始，为期{days}天，预算大约为：{budget}元。我希望住在{constraint_value}类型的酒店。"
            }}
            """

        else:
            budget = estimate_budget(days, people_number)
            constraint_value = random.sample(list(CUISINE_MAP.keys()), k=random.randint(1, 3))
            cuisines_str = "、".join(constraint_value)
            preference_str = f"我想尝试当地的{cuisines_str}菜。"
            prompt = f"""请根据以下信息创建一个旅行者的查询（query），使用流畅的自然语言文本描述。
            - 旅行天数：{days} 天
            - 人数：{people_number} 人
            - 旅行开始日期：{travel_date}
            - 预算约束：预算为 {budget} 元
            - 饮食偏好：{preference_str}
            ### 要求
            1. 用真实用户的语气表达需求，使 query 自然、富有变化。
            2. 输出JSON结构，格式如下：
            {{
                "days": {days},
                "people_number": {people_number},
                "date": "{travel_date}",
                "preference_constraint": {{
                    "budget": {budget},
                    "cuisines": {json.dumps(constraint_value, ensure_ascii=False)}
                }},
                "query": "请你帮我规划一个{people_number}人的{city_name}旅行方案，时间从{travel_date}开始，为期{days}天，预算大约为：{budget}元。我想尝试{cuisines_str}菜。"
            }}
            """
    else:
        selected_cuisines = random.sample(list(CUISINE_MAP.keys()), k=random.randint(1, 3))
        selected_hotel = random.choice(list(HOTEL_MAP.keys()))
        budget = estimate_budget(days, people_number, hotel_type=selected_hotel)
        prompt = f"""请根据以下信息创建一个旅行者的查询（query），使用流畅的自然语言文本描述。
            - 旅行天数：{days} 天
            - 人数：{people_number} 人
            - 旅行开始日期：{travel_date}
            - 预算约束：预算为 {budget} 元。
            - 饮食偏好：{selected_cuisines}
            - 住宿偏好：{selected_hotel}
            ### 要求
            1. 用真实用户的语气表达需求。
            2. 输出JSON结构，格式如下：
            {{
                "days": {days},
                "people_number": {people_number},
                "date": "{travel_date}",
                "preference_constraint": {{
                    "budget": {budget},
                    "cuisines": {json.dumps(selected_cuisines, ensure_ascii=False)},
                    "hotel": "{selected_hotel}"
                }},
                "query": "请你帮我规划一个{people_number}人的{city_name}旅行方案，时间从{travel_date}开始，为期{days}天，预算大约为：{budget}元。我们喜欢{'、'.join(selected_cuisines)}菜系，希望住{selected_hotel}类型的酒店。"
            }}"""


    messages = [{"role": "system", "content": "你是一个擅长生成旅行查询的助手。"},
                {"role": "user", "content": prompt}]

    try:
        response = llm.get_response(messages, tools=None, max_tokens=1024, temperature=0.2, get_json=True)
        travel_query = json.loads(response)
        travel_query["level"] = difficulty
        return travel_query
    except Exception as e:
        print(f"[错误] 生成失败：{e}")
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--city_en', type=str, default='beijing')
    args = parser.parse_args()

    city_en = args.city_en
    city_zh = CITY_MAP[city_en]
    llm = LLMCaller(platform='XiaoAi', model_name='gpt-4o-mini')

    total_number = 100
    data = []

    difficulty_plan = {
        "Easy": int(total_number * 0.5),
        "Medium": int(total_number * 0.3),
        "Hard": total_number - int(total_number * 0.5) - int(total_number * 0.3)
    }

    difficulty_config = {
        "Easy": (1, 0),
        "Medium": (2, 1),
        "Hard": (3, 2)
    }

    for level, count in difficulty_plan.items():
        days, pref_count = difficulty_config[level]
        for i in range(count):
            print(f"生成 [{level}] 查询 {i+1}/{count} ...")
            query = generate_travel_query(city_zh, llm, days, pref_count, level)
            if query:
                data.append(query)
            time.sleep(0.5)

    df = pd.DataFrame(data)
    df.to_csv(f"../database/{city_en}/travel_queries.csv", index=False, encoding="utf-8-sig")