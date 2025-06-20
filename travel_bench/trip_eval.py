import sys
sys.path.append("..")

import argparse
from config import CITY_MAP, CUISINE_MAP
from tools import search_baidu_transport
import ast
import pandas as pd
import json
from collections import defaultdict


def is_valid_fields(plan):
    info_list = ['date', 'num_people', 'visit_attractions', 'breakfast',
                 'lunch', 'dinner', 'accommodation', 'transportation', 'cost_per_capita']
    for day in range(len(plan)):
        day_plan = plan[day]
        for info in info_list:
            if info not in day_plan or not day_plan[info]:
                return False, f'{info} Info Missing for Day {day + 1}'
    return True, None


def is_valid_days(query_data, plan):
    if query_data['days'] == len(plan):
        return True, None
    else:
        return False, "Invalid Num of Planning Days"


def is_valid_peoples(query_data, plan):
    for day_plan in plan:
        if query_data['people_number'] != day_plan['num_people']:
            return False, "Invalid Num of Planning Peoples"
    return True, None


def is_valid_attractions(plan, city_en):
    all_attractions = pd.read_csv(f'../database/{city_en}/amap/attraction_cache.csv')['name'].values
    for day_plan in plan:
        if day_plan.get('visit_attractions'):
            attractions = day_plan['visit_attractions']
            for attract in attractions:
                if attract not in all_attractions:
                    return False, "Invalid Attraction"
    return True, None

def is_valid_restaurants(plan, city_en):
    all_restaurants = pd.read_csv(f'../database/{city_en}/amap/restaurant_cache.csv')['name'].values
    for day_plan in plan:
        restaurants = [day_plan.get(diet).get('name') for diet in ['breakfast', 'lunch', 'dinner']
                       if isinstance(day_plan.get(diet), dict)]
        for rest in restaurants:
            if rest not in all_restaurants:
                return False, "Invalid Restaurant"
    return True, None


def is_valid_accommodations(plan, city_en):
    all_accommodations = pd.read_csv(f'../database/{city_en}/amap/hotel_cache.csv')['name'].values
    for day in range(len(plan)):
        day_plan = plan[day]
        accommodation = day_plan.get("accommodation")
        if not isinstance(accommodation, dict) or not accommodation:
            return False, f"Accommodation Missing on Day {day + 1}"
        acc_name = accommodation.get("name")
        if acc_name not in all_accommodations:
            return False, f"Invalid Accommodation '{acc_name}' on Day {day + 1}"
    return True, None

def is_no_repeated_attractions(plan):
    observed_attractions = []
    error_info = "Attraction is Repeated"
    for day_plan in plan:
        if day_plan.get('visit_attractions'):
            attractions = day_plan['visit_attractions']
            for attract in attractions:
                if attract not in observed_attractions:
                    observed_attractions.append(attract)
                else:
                    return False, error_info
    return True, None

def is_no_repeated_restaurants(plan):
    observed_restaurants = []
    def check_and_add_restaurant(restaurant_name):
        if restaurant_name not in observed_restaurants:
            observed_restaurants.append(restaurant_name)
            return True
        return False

    for day_plan in plan:
        if 'breakfast' in day_plan and 'name' in day_plan['breakfast']:
            if not check_and_add_restaurant(day_plan['breakfast']['name']):
                return False, "Restaurant is Repeated in Breakfast"
        if 'lunch' in day_plan and 'name' in day_plan['lunch']:
            if not check_and_add_restaurant(day_plan['lunch']['name']):
                return False, "Restaurant is Repeated in Lunch"
        if 'dinner' in day_plan and 'name' in day_plan['dinner']:
            if not check_and_add_restaurant(day_plan['dinner']['name']):
                return False, "Restaurant is Repeated in Dinner"
    return True, None


def is_available_transportation(plan, city_en):
    city_zh = CITY_MAP[city_en]
    for day_plan in plan:
        if day_plan.get('transportation') and day_plan.get('transportation') != '-':
            transport_dict = day_plan['transportation']
            for k, v in transport_dict.items():
                origin, dest = k.split("-")
                query = {"org": origin, "dest": dest, "city_name": city_zh}
                queried_transport = search_baidu_transport(query)
                if v not in queried_transport:
                    return False, "Unavailable Transportation"
    return True, None


def is_reasonable_budget(query_data, plan):
    pre_budget = eval(query_data['preference_constraint'])['budget']
    total_cost = 0
    for day_plan in plan:
        day_cost = sum([float(x) if x != 'N/A' else 0 for x in day_plan['cost_per_capita'].values()]) * day_plan['num_people']
        total_cost += day_cost
    if total_cost <= pre_budget:
        return True, None
    else:
        return False, "Overspend Budget"


def is_favorite_cuisine(query_data, plan):
    try:
        preference = ast.literal_eval(query_data['preference_constraint'])
    except Exception:
        return True, None

    pre_cuisines = preference.get('cuisines', None)
    if not pre_cuisines:
        return True, None

    cuisine_categories = {category: set(cuisines) for category, cuisines in CUISINE_MAP.items()}
    def get_category(cuisine):
        for category, cuisines in cuisine_categories.items():
            if cuisine in cuisines:
                return category
        return None

    for day_plan in plan:
        cuisines = [day_plan.get(diet, {}).get('cuisines', '') for diet in ['breakfast', 'lunch', 'dinner'] if day_plan.get(diet)]
        cuisines = [cuisine for cuisine in cuisines if cuisine]
        for cuisine in cuisines:
            category = get_category(cuisine)
            if category:
                if category not in pre_cuisines:
                    return False, "Unsatisfied Cuisines"
            elif cuisine not in pre_cuisines:
                return False, "Unsatisfied Cuisines"
    return True, None


def is_preferred_hotel_type(query_data, plan):
    pre_types = eval(query_data['preference_constraint']).get('hotel', None)
    if pre_types:
        for day in range(len(plan)):
            day_plan = plan[day]
            accommodation = day_plan.get('accommodation')
            if not isinstance(accommodation, dict) or not accommodation:
                return False, f"Missing Accommodation Info on Day {day + 1}"

            hotel_type = accommodation.get('type', '')
            if hotel_type not in pre_types:
                return False, f"Unsatisfied Hotel Type on Day {day + 1}"
    return True, None

def commonsense_constraints(query_data, plan, city_en):
    res = {
        "is_valid_fields": is_valid_fields(plan),
        "is_valid_days": is_valid_days(query_data, plan),
        "is_valid_attractions": is_valid_attractions(plan, city_en),
        "is_valid_restaurants": is_valid_restaurants(plan, city_en),
        "is_valid_accommodations": is_valid_accommodations(plan, city_en),
        # "is_available_transportation": is_available_transportation(plan, city_en),
        "is_no_repeated_attractions": is_no_repeated_attractions(plan),
        "is_no_repeated_restaurants": is_no_repeated_restaurants(plan),
    }
    return res

def preference_constraint(query_data, plan):
    res =  {
        "is_reasonable_budget": is_reasonable_budget(query_data, plan),
        "is_favorite_cuisine": is_favorite_cuisine(query_data, plan),
        "is_preferred_hotel_type": is_preferred_hotel_type(query_data, plan),
    }
    return res


def micro_pass_rate(plan_checkouts, typ):
    plan_checkouts = [item[typ] for item in plan_checkouts]
    all_chk_count = 0.
    pass_chk_count = 0.
    for plan_chk in plan_checkouts:
        if plan_chk:
            all_chk_count += len(plan_chk)
            pass_chk_count += sum([float(item[0]) for item in plan_chk.values()])
    return pass_chk_count / all_chk_count


def macro_pass_rate(plan_checkouts, typ):
    plan_checkouts = [item[typ] for item in plan_checkouts]
    all_plan_count = 0.
    pass_plan_count = 0.
    for plan_chk in plan_checkouts:
        all_plan_count += 1
        if plan_chk:
            if all(value[0] for value in plan_chk.values()):
                pass_plan_count += 1
    return pass_plan_count / all_plan_count


def final_pass_rate(plan_checkouts):
    all_plan_count = 0.
    pass_plan_count = 0.
    for plan_chk in plan_checkouts:
        all_plan_count += 1
        if plan_chk['commonsense'] and plan_chk['preference']:
            if (all(value[0] for value in plan_chk['commonsense'].values())) and (
            all(value[0] for value in plan_chk['preference'].values())):
                pass_plan_count += 1
    return pass_plan_count / all_plan_count


def evaluation(query_records, plans, city_en):
    delivery_cnt = 0
    plan_checkouts = []

    commonsense_failure_stat = defaultdict(lambda: {'fail_count': 0, 'reasons': []})
    preference_failure_stat = defaultdict(lambda: {'fail_count': 0, 'reasons': []})

    assert len(query_records) == len(plans)
    for idx in range(len(query_records)):
        query_data = query_records[idx]
        plan = plans[idx]
        if not plan:
            plan_checkouts.append({'commonsense': None, 'preference': None})
            continue

        delivery_cnt += 1
        commonsense = commonsense_constraints(query_data, plan, city_en)
        preference = preference_constraint(query_data, plan)

        for k, v in commonsense.items():
            if not v[0]:
                commonsense_failure_stat[k]['fail_count'] += 1
                commonsense_failure_stat[k]['reasons'].append(v[1])

        for k, v in preference.items():
            if not v[0]:
                preference_failure_stat[k]['fail_count'] += 1
                preference_failure_stat[k]['reasons'].append(v[1])

        plan_checkouts.append({'commonsense': commonsense, 'preference': preference})

    dr = delivery_cnt / len(query_records)
    cpr_mi = micro_pass_rate(plan_checkouts, typ='commonsense')
    cpr_ma = macro_pass_rate(plan_checkouts, typ='commonsense')
    ppr_mi = micro_pass_rate(plan_checkouts, typ='preference')
    ppr_ma = macro_pass_rate(plan_checkouts, typ='preference')
    fpr = final_pass_rate(plan_checkouts)

    print(f"\n✅ Delivery Rate: {dr:.2%}")
    print(f"✅ Commonsense Constraint Micro Pass Rate: {cpr_mi:.2%}")
    print(f"✅ Commonsense Constraint Macro Pass Rate: {cpr_ma:.2%}")
    print(f"✅ Preference Constraint Micro Pass Rate: {ppr_mi:.2%}")
    print(f"✅ Preference Constraint Macro Pass Rate: {ppr_ma:.2%}")
    print(f"✅ Final Pass Rate: {fpr:.2%}")


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--city_en', type=str, default='beijing')
    args = parser.parse_args()
    city_en = args.city_en

    model_name = f'citygpt-travel-{city_en}'
    query_df = pd.read_csv(f'../database/{city_en}/travel_queries.csv', index_col=None, header=0)
    query_list = query_df.to_dict(orient='records')
    with open(f'../output/{city_en}/{model_name}/generated_plans.json', 'r', encoding='utf-8') as file:
        generated_plans = json.load(file)

    pending_plans = []
    for k, v in generated_plans.items():
        if v == "":
            plan_dict = []
        else:
            plan_dict = v
            if isinstance(plan_dict, dict):
                plan_dict = [plan_dict]
        pending_plans.append(plan_dict)

    evaluation(query_list, pending_plans, city_en)






