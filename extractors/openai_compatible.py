"""OpenAI 兼容格式的 LLM 实体抽取器后端。

支持: OpenAI GPT, DeepSeek, 本地 llama.cpp, 以及任何兼容 OpenAI 格式的 API。
"""

import json
import logging
from typing import Optional

from openai import OpenAI

from .base import BaseEntityExtractor

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = open("prompts/extract_entities.txt", encoding="utf-8").read()


class OpenAICompatibleExtractor(BaseEntityExtractor):
    """使用 OpenAI 兼容 API 的实体抽取器。"""

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str = "deepseek-chat",
        prompt_template: Optional[str] = None,
    ):
        self.model = model
        self.prompt = prompt_template or DEFAULT_PROMPT
        self.client = OpenAI(api_key=api_key, base_url=api_base)

    def _call_llm(self, text: str) -> str:
        """调用 LLM 并返回响应文本。"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM 调用失败: %s", e)
            return json.dumps({"entities": [], "relations": []})
