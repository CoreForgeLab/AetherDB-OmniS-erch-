"""实体抽取器抽象基类。"""

from abc import ABC, abstractmethod
from typing import Any

# 允许的实体类型
VALID_ENTITY_TYPES = {
    "character", "faction", "location", "rule",
    "event", "item", "concept", "system",
}

class BaseEntityExtractor(ABC):
    """实体抽取器基类。子类只需实现 _call_llm(text) 返回原始文本。"""

    @abstractmethod
    def _call_llm(self, text: str) -> str:
        """调用 LLM 并返回原始响应文本。"""
        ...

    def extract(self, text: str) -> dict[str, list[dict[str, Any]]]:
        """从自然语言文本中提取实体和关系。

        返回格式:
        {
            "entities": [
                {"title": "...", "type": "character", "content": "...", "tags": [...], "importance": 3},
            ],
            "relations": [
                {"source": "...", "target": "...", "relation_type": "...", "description": "..."},
            ],
        }
        """
        raw = self._call_llm(text)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> dict[str, list[dict[str, Any]]]:
        """解析 LLM 返回的 JSON。"""
        import json
        import re

        # 尝试提取 JSON（兼容 markdown 包裹的情况）
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            import logging
            logging.getLogger(__name__).warning(
                "LLM 返回的 JSON 解析失败，返回空结果。原文片段: %s", raw[:200]
            )
            return {"entities": [], "relations": []}

        entities = data.get("entities", [])
        relations = data.get("relations", [])

        # 校验实体字段
        validated_entities = []
        for ent in entities:
            title = (ent.get("title") or "").strip()
            if not title:
                continue
            etype = ent.get("type", "concept")
            if etype not in VALID_ENTITY_TYPES:
                etype = "concept"
            validated_entities.append({
                "title": title,
                "type": etype,
                "content": (ent.get("content") or "").strip(),
                "tags": ent.get("tags") or [],
                "importance": max(1, min(5, int(ent.get("importance", 3)))),
            })

        # 校验关系字段
        validated_relations = []
        for rel in relations:
            source = (rel.get("source") or "").strip()
            target = (rel.get("target") or "").strip()
            if not source or not target:
                continue
            validated_relations.append({
                "source": source,
                "target": target,
                "relation_type": (rel.get("relation_type") or "related_to").strip(),
                "description": (rel.get("description") or "").strip(),
            })

        return {"entities": validated_entities, "relations": validated_relations}
