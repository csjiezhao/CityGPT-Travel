from llm_api import LLMCaller
from tools import tools_map, tools_desc
from prompts import REACT_PROMPT
import ast
import re
import json


class Notebook:
    def __init__(self):
        self.data = None
        self.date_list = None

    def init(self, params):
        if type(params) == str:
            params = ast.literal_eval(params)
        self.date_list = params['dates']
        self.data = [{"date": d,
                      "num_people": params['num_people'],
                      "visit_attractions": [],
                      "breakfast": {},
                      "lunch": {},
                      "dinner": {},
                      "accommodation": {},
                      "transportation": {},
                      "cost_per_capita": {}
                      } for d in self.date_list]
        return '笔记本初始化成功！'

    def write(self, info):

        if not self.data:
            return "写入失败：还没初始化笔记本，请先调用NotebookInit工具"

        if not self.date_list or not isinstance(self.date_list, list):
            return "写入失败：尚未初始化或日期格式错误，请先调用 NotebookInit 工具。"

        if type(info) == str:
            info = ast.literal_eval(info)
        typ = info['info_class']
        if typ not in ['attraction', 'breakfast', 'lunch', 'dinner', 'accommodation', 'transportation']:
            return "写入信息类型错误！类型必须是['attraction', 'breakfast', 'lunch', 'dinner', 'accommodation', 'transportation']之一"

        cur_date = info['date']
        try:
            idx = self.date_list.index(cur_date)
        except ValueError:
            return f"写入失败：在笔记本中找不到日期 {cur_date} 。"

        cur_data = info['data']

        if typ == 'attraction':
            for attr_dict in cur_data:
                if not all(k in attr_dict for k in ['name','cost']):
                    return "写入的景点信息缺少必要字段，请确保包含 name 和 cost。"
                attr_name = attr_dict['name']
                attr_cost = attr_dict['cost']
                self.data[idx]['visit_attractions'].append(attr_name)
                self.data[idx]['cost_per_capita'][attr_name] = attr_cost

        elif typ in ['breakfast', 'lunch', 'dinner']:
            if not all(k in cur_data for k in ['name', 'keytag', 'cost']):
                return "写入的餐厅信息缺少必要字段，请确保包含 name、keytag 和 cost。"
            self.data[idx][typ]['name'] = cur_data['name']
            self.data[idx][typ]['cuisines'] = cur_data['keytag']
            self.data[idx]['cost_per_capita'][typ] = cur_data['cost']

        elif typ == 'accommodation':
            if not all(k in cur_data for k in ['name', 'keytag', 'cost']):
                return "写入的住宿信息缺少必要字段，请确保包含 name、keytag 和 cost。"
            self.data[idx][typ] = {
                "name": cur_data['name'],
                "type": cur_data['keytag']
            }
            self.data[idx]['cost_per_capita'][typ] = cur_data['cost']

        elif typ == 'transportation':
            if not 'cost' in cur_data:
                return "写入的交通信息缺少cost字段！"
            self.data[idx]['cost_per_capita']['transit'] = (
                    self.data[idx]['cost_per_capita'].get('transit', 0.) + cur_data.get('cost', 0.))
            self.data[idx][typ].update({k: v for k, v in cur_data.items() if k != 'cost'})
        return "信息写入成功！"

    def read(self):
        return self.data


class ReActTravelAgent:
    def __init__(self, platform, model_name):
        self.platform = platform
        self.model_name = model_name
        self.llm = LLMCaller(platform, model_name)
        self.notebook = Notebook()
        self.tools = tools_map
        self.tools['NotebookInit'] = self.notebook.init
        self.tools['NotebookWrite'] = self.notebook.write
        self.tools['PlanOutput'] = self.notebook.read

        self.max_steps = 50
        self.query = None
        self.finished = False
        self.__reset_agent()

    def __reset_agent(self):
        self.step_n = 1
        self.finished = False
        self.messages = [{"role": "system", "content": REACT_PROMPT},
                         {"role": "user", "content": self.query}]
        self.notebook.__init__()

    def _prune_messages(self, drop_observations=True, keep_last_observations=3):
        obs_indices = []
        for idx, msg in enumerate(self.messages):
            if msg['role'] == 'assistant' and msg['content'].startswith('Observation'):
                obs_indices.append(idx)

        keep_obs_indices = set(obs_indices[-keep_last_observations:]) if drop_observations else set(obs_indices)

        self.messages = [
            msg for idx, msg in enumerate(self.messages)
            if not (msg['role'] == 'user' and '你接下来要进行的是' in msg['content']) and
               not (idx in obs_indices and idx not in keep_obs_indices)
        ]

    def plan_trip(self, query, reset=True):
        self.query = query
        if reset:
            self.__reset_agent()

        while not self.finished and not self.is_halted():
            self.step()
        return self.notebook.data

    def step(self, is_log=False):
        self._prune_messages(keep_last_observations=2)

        thought = self.thought()
        self.messages.append({"role": "assistant", "content": thought})
        if is_log:
            print(thought)
        action = self.action()
        if action["type"] == "tool_call":
            tool_name = action["tool_name"]
            raw_args = action["tool_args"]
            parse_info = 'done'
        else:  # action["type"] == "message"
            tool_name, raw_args, parse_info = self.parse_tool_call_from_message(action['content'])

        if self.finish_detect(tool_name):
            self.finished = True
            return

        if tool_name and raw_args:
            act_msg = f"Action {self.step_n}: {tool_name}{raw_args}"
            try:
                args = ast.literal_eval(raw_args)
                if not isinstance(args, dict):
                    obs_msg = f"Observation {self.step_n}: 工具调用失败，参数必须是dict类型！"
                else:
                    result = self.observation(tool_name, args)
                    obs_msg = f"Observation {self.step_n}: {result}"
            except Exception as e:
                obs_msg = f"Observation {self.step_n}: 工具调用参数解析失败: {e}，请重新确认要执行的动作！"
        else: # 工具名和参数没有成功解析
            text = action['content']
            text = re.sub(r'Action\s+\d+:\s*', '', text)
            act_msg = f"Action {self.step_n}: {text}..."
            if parse_info == 'no_tool':
                obs_msg = f"Observation {self.step_n}: Action的工具调用格式不正确，没有解析出任何可用的工具，请重新思考生成合理的动作！"
            elif parse_info == 'more_tools':
                obs_msg = f"Observation {self.step_n}: 每次Action只能调用一个工具，且不能重复调用同一工具。请调整思路，生成更合理的工具调用。"
            else:
                obs_msg = f"Observation {self.step_n}: {tool_name}的参数不合规，请重新思考生成合理的动作参数！"

        self.messages.append({"role": "assistant", "content": act_msg})
        self.messages.append({"role": "assistant", "content": obs_msg})
        if is_log:
            print(act_msg)
            print(obs_msg)
        self.step_n += 1

    def parse_tool_call_from_message(self, content):
        # Step 1: 优先尝试从 ```json ... ``` 中提取结构化调用
        match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            try:
                json_block = match.group(1)
                tool_calls = json.loads(json_block)
                if not isinstance(tool_calls, list):
                    return None, None, 'args_error'
                if len(tool_calls) > 1:
                    return None, None, 'more_tools'
                if len(tool_calls) == 0:
                    return None, None, 'no_tool'

                tool_call = tool_calls[0]
                if not isinstance(tool_call, dict) or len(tool_call) != 1:
                    return None, None, 'args_error'

                tool_name = list(tool_call.keys())[0]
                args_dict = tool_call[tool_name]
                if not isinstance(args_dict, dict):
                    return tool_name, None, 'args_error'

                raw_args = json.dumps(args_dict, ensure_ascii=False)
                return tool_name, raw_args, 'done'

            except json.JSONDecodeError:
                return None, None, 'args_error'

        pattern = r"|".join(re.escape(tool) for tool in self.tools)
        matched_tools = re.findall(rf"({pattern})\s*\{{", content)
        if len(matched_tools) == 0:
            return None, None, 'no_tool'
        if len(matched_tools) > 1:
            return None, None, 'more_tools'
        tool_name = matched_tools[0]
        start_index = content.find('{', content.find(tool_name))
        end_index = content.rfind('}', start_index) + 1
        raw_args = content[start_index:end_index]
        if raw_args:
            return tool_name, raw_args, 'done'
        else:
            return tool_name, None, 'args_error'

    @staticmethod
    def finish_detect(tool_name):
        return tool_name in {"PlanOutput"}

    def thought(self):
        self.messages.append({"role": "user", "content": "你接下来要进行的是Thought"})
        response = self.llm.get_response(self.messages, tools=None, max_tokens=512)
        if response["type"] == "message":
            content = response["content"].strip()
            content = content.split("Action")[0].strip() if "Action" in content else content
            if not content:
                content = "当前信息不足，我将继续推理。"

            content = re.sub(r"^.*?Thought \d+: ", "", content)  # 移除 Thought {N}: 前缀及之前的内容
            content = re.sub(r"^.*?Thought", "", content)  # 移除 Thought 前缀及之前的内容
            content = f"Thought {self.step_n}: {content}"
            return content
        return f"Thought {self.step_n}: 当前信息不足，但我会继续推理。"

    def action(self):
        self.messages.append({"role": "user", "content": "你接下来要进行的是Action"})
        return self.llm.get_response(self.messages, tools=tools_desc, max_tokens=512)

    def observation(self, tool_name, tool_args):
        if tool_name not in self.tools:
            return f"错误：'{tool_name}' 不是可用工具！"
        try:
            func = self.tools[tool_name]
            if tool_name == "PlanOutput":
                result = func()
            else:
                result = func(tool_args)
            if not isinstance(result, str):
                result = str(result)
            return result.strip()
        except Exception as e:
            return f"调用工具 {tool_name} 失败，错误信息：{str(e)}"

    def is_halted(self):
        return (self.step_n > self.max_steps) and not self.finished