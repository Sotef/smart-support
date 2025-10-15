import json
import os
import math
from typing import List, Tuple, Dict, Any, Optional


class VectorIndex:
    """
    Простой персистентный vector index на JSON (ids + vectors) с cosine-поиском.
    Подходит для небольших КБ; без внешних зависимостей.
    """
    def __init__(self, path: str = "data/kb_index.json"):
        self.path = path
        self.model: Optional[str] = None
        self.dim: Optional[int] = None
        self.ids: List[str] = []
        self.vectors: List[List[float]] = []

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def load(self) -> bool:
        if not self.exists():
            return False
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.model = data.get("model")
        self.dim = data.get("dim")
        self.ids = data.get("ids", [])
        self.vectors = data.get("vectors", [])
        return True

    def save(self, model: str, dim: int, ids: List[str], vectors: List[List[float]]):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        payload = {
            "model": model,
            "dim": dim,
            "ids": ids,
            "vectors": vectors,
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        self.model = model
        self.dim = dim
        self.ids = ids
        self.vectors = vectors

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        s = 0.0
        na = 0.0
        nb = 0.0
        for x, y in zip(a, b):
            s += x * y
            na += x * x
            nb += y * y
        na = math.sqrt(na) or 1.0
        nb = math.sqrt(nb) or 1.0
        val = s / (na * nb)
        return max(0.0, min(1.0, val))

    def search(self, query_vec: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        """Возвращает [(id, score)] отсортированные по убыванию score."""
        if not self.vectors:
            return []
        scores: List[Tuple[str, float]] = []
        for _id, vec in zip(self.ids, self.vectors):
            scores.append((_id, self._cosine(query_vec, vec)))
        scores.sort(key=lambda t: t[1], reverse=True)
        return scores[:top_k]

    def add_or_update(self, _id: str, vec: List[float]):
        if self.dim is None:
            self.dim = len(vec)
        if len(vec) != self.dim:
            raise ValueError("Vector dimension mismatch")
        try:
            idx = self.ids.index(_id)
            self.vectors[idx] = vec
        except ValueError:
            self.ids.append(_id)
            self.vectors.append(vec)
        # Автосохранение
        self.save(self.model or "unknown", self.dim, self.ids, self.vectors)
