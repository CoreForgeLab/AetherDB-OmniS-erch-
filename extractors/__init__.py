"""抽取器工厂函数 — 根据配置返回对应的抽取器实例。"""

import logging
from typing import Any

from .base import BaseEntityExtractor

logger = logging.getLogger(__name__)


def get_extractor(config: dict[str, Any]) -> BaseEntityExtractor:
    """根据配置字典返回抽取器实例。

    config 示例:
    {
        "backend": "openai_compatible",
        "openai_compatible": {
            "api_base": "https://api.deepseek.com/v1",
            "api_key": "sk-xxx",
            "model": "deepseek-chat"
        },
        "prompt_template": "prompts/extract_entities.txt"
    }

    或:
    {
        "backend": "ollama",
        "ollama": {
            "model": "qwen2.5:7b",
            "host": "localhost:11434"
        }
    }
    """
    backend = config.get("backend", "openai_compatible")

    if backend == "openai_compatible":
        from .openai_compatible import OpenAICompatibleExtractor

        oc_config = config.get("openai_compatible", {})
        prompt = config.get("prompt_template")
        return OpenAICompatibleExtractor(
            api_base=oc_config.get("api_base", "https://api.deepseek.com/v1"),
            api_key=oc_config.get("api_key", ""),
            model=oc_config.get("model", "deepseek-chat"),
            prompt_template=prompt,
        )

    elif backend == "ollama":
        from .ollama import OllamaExtractor

        ol_config = config.get("ollama", {})
        prompt = config.get("prompt_template")
        return OllamaExtractor(
            model=ol_config.get("model", "qwen2.5:7b"),
            host=ol_config.get("host", "localhost:11434"),
            prompt_template=prompt,
        )

    else:
        raise ValueError(f"不支持的 LLM 后端: {backend}，可选: openai_compatible, ollama")
