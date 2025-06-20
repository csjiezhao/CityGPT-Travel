import sys
sys.path.append("..")

from prompts import KNOW_EVAL_PROMPT
from llm_api import LLMCaller

import os
import json
import numpy as np
import argparse


def mc_eval(llm, mc_dict):
    cnt = 0.
    for idx, mc in enumerate(mc_dict):
        messages = [{"role": "system", "content": KNOW_EVAL_PROMPT},
                    {"role": "user", "content":
                        "Question: " + mc['question'] + "\n" +
                        "\n ".join(f"{key} {value}" for key, value in mc['options'].items())}]
        correct_answer = mc['correct_answer']
        response = llm.get_response(messages, tools=None)['content']
        answer = response.strip().replace(" ", "").replace("\n", "")
        if answer == correct_answer:
            cnt += 1
    return cnt / len(mc_data)



if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--city_en', type=str, default='shanghai')
    parser.add_argument('--platform', type=str, default='vLLM')
    args = parser.parse_args()
    platform = args.platform
    city_en = args.city_en
    model_name = 'citygpt-travel-'+ city_en

    CITY_FILES = ['road_len_mc.json', 'road_link_mc.json', 'road_od_mc.json', 'poi_mc.json']
    TRIP_FILES = ['attractions_address_mc.json', 'attractions_price_mc.json', 'attractions_open_time_mc.json',
                  'restaurants_address_mc.json', 'restaurants_price_mc.json', 'restaurants_tag_mc.json',
                  'hotels_address_mc.json', 'hotels_price_mc.json']

    print(f"City: {city_en}-------------------------------------------------->")
    base_dir = f'../database/{city_en}/eval/mc'
    llm = LLMCaller(platform=platform, model_name=model_name)
    city_qa = []
    for file in CITY_FILES:
        with open(os.path.join(base_dir, file), 'r', encoding='utf-8') as f:
            mc_data = json.load(f)
        acc = mc_eval(llm, mc_data)
        city_qa.append(acc)
    city_qa = np.mean(city_qa)
    print(city_en, "CityQA:", city_qa)
    trip_qa = []
    for file in TRIP_FILES:
        with open(os.path.join(base_dir, file), 'r', encoding='utf-8') as f:
            mc_data = json.load(f)
        acc = mc_eval(llm, mc_data)
        trip_qa.append(acc)
    trip_qa = np.mean(trip_qa)
    print(city_en, "TripQA:", trip_qa)