"""Ollama 本地模型实体抽取器后端。"""

import json
import logging
from typing import Optional

import requests

from .base import BaseEntityExtractor

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = open("prompts/extract_entities.txt", encoding="utf-8").read()


class OllamaExtractor(BaseEntityExtractor):
    """使用 Ollama 本地模型的实体抽取器。"""

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        host: str = "localhost:11434",
        prompt_template: Optional[str] = None,
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.prompt = prompt_template or DEFAULT_PROMPT

    def _call_llm(self, text: str) -> str:
        """调用 Ollama API 并返回响应文本。"""
        try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.prompt},
                        {"role": "user", "content": text},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error("Ollama 调用失败: %s", e)
            return json.dumps({"entities": [], "relations": []})
