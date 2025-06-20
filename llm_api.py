from dotenv import load_dotenv
from config import WAIT_TIME_MIN, WAIT_TIME_MAX, ATTEMPT_COUNTER, PROXY, MODEL_DICT

import httpx
from openai import OpenAI
import os
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential
)
load_dotenv()


def get_api_key(platform):
    return os.environ[f'{platform}_API_KEY']


class LLMCaller:
    def __init__(self, platform, model_name):
        if platform == "OpenAI":
            self.client = OpenAI(
                api_key=get_api_key('OpenAI'),
                base_url='https://api.openai.com/v1',
                http_client=httpx.Client(proxy=PROXY),
            )
        elif platform == "SiliconFlow":
            self.client = OpenAI(
                base_url="https://api.siliconflow.cn/v1",
                api_key=get_api_key(platform)
            )
        elif platform == "DeepInfra":
            self.client = OpenAI(
                api_key=get_api_key(platform),
                http_client=httpx.Client(proxy=PROXY),
                base_url="https://api.deepinfra.com/v1/openai",
            )
        elif platform == 'vLLM':
            self.client = OpenAI(
                base_url="http://localhost:23199/v1",
                api_key=get_api_key(platform),
            )
        self.model_name = MODEL_DICT.get(model_name).get(platform)

    @retry(wait=wait_random_exponential(min=WAIT_TIME_MIN, max=WAIT_TIME_MAX), stop=stop_after_attempt(ATTEMPT_COUNTER))
    def get_response(self, messages, tools, max_tokens=1024, temperature=0., get_json=False):
        params = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        if get_json:
            params["response_format"] = {"type": "json_object"}

        completion = self.client.chat.completions.create(**params)
        msg = completion.choices[0].message
        # Case 1: 模型触发了工具调用
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            return {
                "type": "tool_call",
                "tool_name": msg.tool_calls[0].function.name,
                "tool_args": msg.tool_calls[0].function.arguments
            }

        if get_json:
            return msg.content.strip()
        else:
            return {
                "type": "message",
                "content": msg.content.strip() if msg.content else ""
            }
