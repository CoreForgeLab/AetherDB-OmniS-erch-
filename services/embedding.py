import math
import time
import sqlite3
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import requests
import json
import os

VECTOR_DIMS = 1024  # bge-m3

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass
    @abstractmethod
    def dims(self) -> int:
        pass

class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dims: int = VECTOR_DIMS):
        self._dims = dims
    def embed(self, text: str) -> List[float]:
        h = hash(text)
        import random
        r = random.Random(h)
        vec = [r.random() - 0.5 for _ in range(self._dims)]
        mag = math.sqrt(sum(x*x for x in vec))
        return [x/mag for x in vec]
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]
    def dims(self) -> int:
        return self._dims

class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str = 'http://localhost:11434', model: str = 'bge-m3'):
        self.base_url = base_url
        self.model = model
        self._dims = VECTOR_DIMS
    def embed(self, text: str) -> List[float]:
        resp = requests.post(f'{self.base_url}/api/embeddings', json={'model': self.model, 'prompt': text}, timeout=30)
        resp.raise_for_status()
        return resp.json()['embedding']
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        results = []
        for t in texts:
            results.append(self.embed(t))
            time.sleep(0.05)
        return results
    def dims(self) -> int:
        return self._dims
