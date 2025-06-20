from config import CITY_MAP, ROOT_PATH
import pandas as pd
import requests
import os
import json
import hashlib

from dotenv import load_dotenv
load_dotenv()

BAIDU_API_KEY=os.environ["BAIDU_API_KEY"]
CITY_MAP = {value: key for key, value in CITY_MAP.items()}

CACHE_DIR = f"{ROOT_PATH}/database/transport_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_key(params: dict) -> str:
    raw = json.dumps(params, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def load_from_cache(cache_key):
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_to_cache(cache_key, result):
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

def normalize_city_name(name):
    if not name.endswith("市"):
        return name + "市"
    return name

def search_attraction_cache(params):
    if type(params) == str:
        params = eval(params)
    city_zh = normalize_city_name(params['city_name'])
    city_en = CITY_MAP[city_zh]
    df = pd.read_csv(f'database/{city_en}/amap/attraction_cache.csv', index_col=None)
    df['cost'] = df['cost'].astype(float)
    df = df.fillna(0)
    df = df[['name', 'cost']]
    # df = df.iloc[:30]
    df = df.to_dict(orient='records')
    return "工具返回的景点信息是：" + str(df)

def search_nearby_restaurant_cache(params):
    if type(params) == str:
        params = eval(params)
    attraction = params['attraction']
    city_zh = normalize_city_name(params['city_name'])
    city_en = CITY_MAP[city_zh]
    df = pd.read_csv(f'database/{city_en}/amap/restaurant_cache.csv', index_col=None)
    df = df[df['attraction'] == attraction]
    df['cost'] = df['cost'].astype(float)
    df = df.fillna('N/A')
    df = df[['name', 'cost', 'keytag']]
    df = df.iloc[:30]
    df = df.to_dict(orient='records')
    return "工具返回的餐厅信息是：" + str(df)

def search_nearby_hotel_cache(params):
    if type(params) == str:
        params = eval(params)
    attraction = params['attraction']
    city_zh = normalize_city_name(params['city_name'])
    city_en = CITY_MAP[city_zh]
    df = pd.read_csv(f'database/{city_en}/amap/hotel_cache.csv', index_col=None)
    df = df[df['attraction'] == attraction]
    df['cost'] = df['cost'].astype(float)
    df = df.fillna('N/A')
    df = df[['name', 'cost', 'keytag']]
    df = df.iloc[:30]
    df = df.to_dict(orient='records')
    return "工具返回的住宿信息是：" + str(df)

def search_baidu_transport(params):
    if isinstance(params, str):
        params = json.loads(params)

    cache_key = get_cache_key(params)
    cache_result = load_from_cache(cache_key)
    if cache_result:
        return cache_result

    org = params['org']
    dest = params['dest']
    city_zh = normalize_city_name(params['city_name'])
    url = "https://api.map.baidu.com/direction/v2/transit"
    params = {
        "origin": get_baidu_coordinates(org, city_zh),
        "destination": get_baidu_coordinates(dest, city_zh),
        "page_size": 1,
        "page_index": 1,
        "ak": BAIDU_API_KEY,
    }
    response = requests.get(url=url, params=params)
    if response.status_code == 200:
        parsed = parse_baidu_transport_info(org, dest, response.json())
        save_to_cache(cache_key, parsed)
        return parsed
    else:
        return f"API请求失败，状态码: {response.status_code}, 错误信息: {response.text}"

def get_baidu_coordinates(address, city='北京市'):
    url = "https://api.map.baidu.com/geocoding/v3"
    params = {
        "address": address,
        "output": "json",
        "city": city,
        "ak": BAIDU_API_KEY,
    }
    response = requests.get(url=url, params=params)
    if response.status_code == 200:
        loc = response.json().get('result').get('location')
        lng = loc.get('lng')
        lat = loc.get('lat')
        return f"{lat:.6f}" + "," + f"{lng:.6f}"
    else:
        return f"API请求失败，状态码: {response.status_code}, 错误信息: {response.text}"

def parse_baidu_transport_info(origin, dest, response):
    routes = response.get('result').get('routes')
    parsed_info = []
    for idx, route in enumerate(routes):
        route_info = [seg.get('instructions') for step in route.get('steps') for seg in step]
        route_info = f"-路线{idx}[距离{route.get('distance')}米，耗时{route.get('duration')}秒，花费{route.get('price')}元]: 从{origin}出发," + '-->'.join(filter(None, route_info)) + f"到达{dest}"
        parsed_info.append(route_info)
    taxi = response.get('result', {}).get('taxi')
    if taxi and taxi.get('detail'):
        taxi_info = f"-出租车[距离{taxi.get('distance')}米，耗时{taxi.get('duration')}秒，花费{taxi.get('detail')[0].get('total_price')}元]"
        parsed_info.append(taxi_info)
    parsed_info = f"查询到{origin}到{dest}的交通信息\n" + '\n'.join(parsed_info)
    return parsed_info

tools_map = {
    "AttractionSearch": search_attraction_cache,
    "NearbyRestaurantSearch": search_nearby_restaurant_cache,
    "NearbyHotelSearch": search_nearby_hotel_cache,
    "TransportationSearch": search_baidu_transport,
}


tools_desc = [
    {
        "type": "function",
        "function": {
            "name": "AttractionSearch",
            "description": "搜索指定城市的景点信息，返回名称和票价等数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "城市中文名称，例如：北京市"
                    }
                },
                "required": ["city_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "NearbyRestaurantSearch",
            "description": "查询指定城市中某个景点附近的餐厅信息，包括名称、类型和价格等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "attraction": {
                        "type": "string",
                        "description": "景点名称，例如：故宫博物院"
                    },
                    "city_name": {
                        "type": "string",
                        "description": "景点所在城市的中文名称，例如：北京市"
                    }
                },
                "required": ["attraction", "city_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "NearbyHotelSearch",
            "description": "查询指定城市中某个景点附近的酒店信息，包括名称、类型和价格等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "attraction": {
                        "type": "string",
                        "description": "景点名称，例如：故宫博物院"
                    },
                    "city_name": {
                        "type": "string",
                        "description": "景点所在城市的中文名称，例如：北京市"
                    }
                },
                "required": ["attraction", "city_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "TransportationSearch",
            "description": "查询指定城市中两个景点之间的交通路线，包括公交、步行或打车方式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "org": {
                        "type": "string",
                        "description": "出发地名称，例如：颐和园"
                    },
                    "dest": {
                        "type": "string",
                        "description": "目的地名称，例如：清华大学"
                    },
                    "city_name": {
                        "type": "string",
                        "description": "城市中文名称，例如：北京市"
                    }
                },
                "required": ["org", "dest", "city_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "NotebookInit",
            "description": "初始化旅行笔记本，设定出行日期和人数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dates": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "出行日期，格式如 '2025-06-01'"
                        },
                        "description": "出行的所有日期列表"
                    },
                    "num_people": {
                        "type": "integer",
                        "description": "出行人数"
                    }
                },
                "required": ["dates", "num_people"]
            }
        }
    },
{
  "type": "function",
  "function": {
    "name": "NotebookWrite",
    "description": "将收集到的行程信息写入笔记本。支持六种类型信息的写入：景点、美食（三餐）、住宿、交通。",
    "parameters": {
      "type": "object",
      "properties": {
        "date": {
          "type": "string",
          "description": "要写入的日期，格式为 'YYYY-MM-DD'，必须是 NotebookInit 初始化时设定的某天。"
        },
        "info_class": {
          "type": "string",
          "enum": ["attraction", "breakfast", "lunch", "dinner", "accommodation", "transportation"],
          "description": "写入信息的类型。"
        },
        "data": {
          "description": "要写入的数据内容，因info_class取值而异："
                         "-若 info_class = 'attraction'，则 data 是 [{'name':{景点名称}, 'cost':float}, {...}]"
                         "-若 info_class = 'breakfast'/'lunch'/'dinner'/'accommodation'，则 data 是 {'name': str, 'keytag': str, 'cost':float}"
                         "-若 info_class = 'transportation'，则 data 是 {'{org}-{dest}':'从XXX出发,步行373米-->...', 'cost':float}",
        }
      },
      "required": ["date", "info_class", "data"]
    }
  }
},

    {
        "type": "function",
        "function": {
            "name": "PlanOutput",
            "description": "输出当前的旅行计划。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
