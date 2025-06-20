import sys

if sys.platform.startswith("win"):
    PROXY = "http://127.0.0.1:10809"
elif sys.platform.startswith("linux"):
    PROXY = "http://127.0.0.1:10190"
elif sys.platform.startswith("darwin"):
    PROXY = "http://127.0.0.1:10808"

WAIT_TIME_MIN = 3
WAIT_TIME_MAX = 60
ATTEMPT_COUNTER = 10

ROOT_PATH = '/usr/exp/CityGPT-Travel'  # replace it with your experimental path

CITY_MAP = {'beijing': '北京市', 'shanghai': '上海市', 'guangzhou':'广州市', 'chengdu':'成都市', 'xian':'西安市'}

CUISINE_MAP = {
    "中餐": [
        '中餐', '中餐厅', '北京菜', '东北菜', '川菜', '乐山川菜', '四川火锅', '串串香', '麻辣烫',
        '鲁菜', '湘菜', '徽菜', '粤菜', '广府菜', '闽菜', '江浙菜', '浙菜', '苏菜', '羊蝎子火锅'
        '上海菜', '湖北菜', '江西菜', '河南菜', '河北菜', '山西菜', '陕西菜', '天津菜',
        '新疆菜', '内蒙菜', '云南菜', '贵州菜', '广西菜', '海南菜', '清真菜', '客家菜', '淮扬菜',
        '潮州菜', '潮汕火锅', '农家菜', '家常菜', '私房菜', '盐帮菜', '锅盔', '锅盖面', '钵钵鸡',
        '猪脚饭', '砂锅', '砂锅粥', '石锅拌饭', '石锅鱼', '干锅', '老北京火锅', '焖锅', '烧烤',
        '烧鸡', '烧鹅', '烧麦', '烧饼', '炖菜'
    ],
    "外国菜": [
        '日本料理', '寿司', '日式火锅', '日式烧烤', '日式自助',
        '韩国料理', '韩式烤肉',
        '印度菜', '泰国菜', '越南菜', '东南亚菜', '其它亚洲菜', '泰式火锅',
        '意大利菜', '意式菜品餐厅', '法国菜', '法式菜品餐厅', '德国菜', '俄国菜',
        '西班牙菜', '非洲菜', '墨西哥菜', '西餐', '西餐厅(综合风味)', '外国餐厅', '澳门菜', '香港菜', '台湾菜'
    ],
    "小吃快餐": [
        '小吃', '小吃快餐', '快餐', '快餐厅', '早餐', '夜宵', '包子', '小笼包', '炸酱面',
        '热干面', '凉皮', '杂酱面', '担担面', '拉面', '刀削面', '炒肝', '凉菜', '汤包',
        '煲仔饭', '米线', '米粉', '粉丝汤', '板面', '肠粉', '螺蛳粉', '潮汕粥',
        '鱼粉', '汤圆', '生煎', '肉夹馍', '驴肉火烧', '猪脚饭', '胡辣汤',
        '酱香饼', '麻辣香锅', '麻辣拌', '铁板烧', '饺子', '馄饨', '饸饹面', '盖饭'
    ],
    "美式快餐": [
        '汉堡包', '披萨', '炸鸡', '三明治', '西式快餐', '炸鱼薯条'
    ],
    "自助餐": [
        '自助快餐', '自助餐', '自助火锅', '自助烤肉', '自助海鲜', '日式自助'
    ],
    "特色餐厅": [
        '融合菜', '创意菜', '主题餐厅', '音乐餐厅', '居酒屋', '茶餐厅', '茶点', '茶座',
        '清吧', '咖啡', '甜品店', '糕点/烘焙', '奶茶/茶饮'
    ],
    "轻食": [
        '轻食', '沙拉'
    ]
}

HOTEL_MAP= {
    "经济型":[],
    "舒适型":[],
    "高档型":[],
    "奢华型":[],
    "民宿客栈":[]
}

MODEL_DICT = {
    'gpt-3.5-turbo': {
        'OpenAI': 'gpt-3.5-turbo-1106',
    },
    'gpt-4o-mini':{
        'OpenAI': 'gpt-4o-mini-2024-07-18',
    },
    'qwen-2.5-7b':{
        'SiliconFlow': 'Qwen/Qwen2.5-7B-Instruct',  # Pro/Qwen/Qwen2.5-7B-Instruct
        'DashScope': 'qwen2.5-7b-instruct',
    },
    'glm-4-9b':{
        'SiliconFlow': 'Pro/THUDM/glm-4-9b-chat',  # Pro/THUDM/glm-4-9b-chat
    },
    'gemma-3-12b':{
        'DeepInfra': 'google/gemma-3-12b-it',
    },
    'citygpt-t-beijing':{
        'vLLM': f'{ROOT_PATH}/model_zoo/beijing/qwen2.5-7b/lora_merged',
    },
    'citygpt-t-shanghai':{
        'vLLM': f'{ROOT_PATH}/model_zoo/shanghai/qwen2.5-7b/lora_merged',
    },
    'citygpt-t-guangzhou':{
        'vLLM': f'{ROOT_PATH}/model_zoo/guangzhou/qwen2.5-7b/lora_merged',
    },
    'citygpt-t-chengdu':{
        'vLLM': f'{ROOT_PATH}/model_zoo/chengdu/qwen2.5-7b/lora_merged',
    },
    'citygpt-t-xian':{
        'vLLM': f'{ROOT_PATH}/model_zoo/xian/qwen2.5-7b/lora_merged',
    }
}