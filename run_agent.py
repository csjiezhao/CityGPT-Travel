from travel_agent import ReActTravelAgent

import argparse
import os
import json
import pandas as pd
import time

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--city_en', type=str, default='beijing')
    parser.add_argument('--platform', type=str, default='OpenAI')
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini')
    args = parser.parse_args()
    city_en = args.city_en
    platform = args.platform
    model_name = args.model_name

    agent = ReActTravelAgent(platform, model_name)
    travel_queries = pd.read_csv(f'database/{city_en}/travel_queries.csv')
    generated_plans = {}
    t1 = time.time()
    for idx, row in travel_queries.iterrows():
        print(f'CITY: {city_en}, MODEL: {model_name}, PLAN: {idx}')
        result = agent.plan_trip(row['query'])
        generated_plans[idx] = result
    output_dir = os.path.join('output', city_en, model_name)
    os.makedirs(output_dir, exist_ok=True)
    output_file_path = os.path.join(output_dir, 'generated_plans.json')
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(generated_plans, ensure_ascii=False, indent=4, separators=(',', ':')))
    t2 = time.time()
    print(f'计划生成耗时：{(t2-t1)/3600}小时')