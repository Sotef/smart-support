from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import re
import math
import hashlib

app = FastAPI(title="Scibox Mock", version="1.0")

# ---------- Models for mock ----------
class AnalyzePayload(BaseModel):
    text: str
    operations: Optional[List[str]] = None

class EmbeddingsPayload(BaseModel):
    model: Optional[str] = None
    input: Union[str, List[str]]

# ---------- Utils ----------
ENTITY_PATTERNS = {
    "phone": r"\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "account_number": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
}

CLASS_KEYWORDS = {
    "technical": ['ошибка','не работает','сбой','баг','error','bug'],
    "billing": ['счет','платеж','оплата','списание','возврат','тариф'],
    "account": ['аккаунт','логин','вход','пароль','восстановление','доступ'],
    "complaint": ['жалоба','недоволен','ужасно','претензия','негативный'],
    "feature_request": ['хочу','добавьте','предлагаю','улучшение','функция'],
}

POS_WORDS = ['хорошо','отлично','спасибо','доволен','нравится','супер']
NEG_WORDS = ['плохо','ужасно','недоволен','проблема','ошибка','кошмар']


def hash_embedding(text: str, dim: int = 384) -> List[float]:
    vec = [0.0] * dim
    tokens = re.findall(r"\b\w+\b", (text or '').lower())
    for tok in tokens:
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v / norm for v in vec]

# ---------- Endpoints ----------
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/analyze")
async def analyze(payload: AnalyzePayload):
    text = payload.text or ""
    entities = []
    for etype, pattern in ENTITY_PATTERNS.items():
        for m in re.finditer(pattern, text, re.IGNORECASE):
            entities.append({
                "text": m.group(),
                "type": etype,
                "confidence": 0.85,
                "start": m.start(),
                "end": m.end(),
            })
    tl = text.lower()
    scores = {k: sum(1 for kw in kws if kw in tl) for k, kws in CLASS_KEYWORDS.items()}
    best_cat = max(scores, key=scores.get) if any(scores.values()) else "general"
    pos = sum(1 for w in POS_WORDS if w in tl)
    neg = sum(1 for w in NEG_WORDS if w in tl)
    sent = 0.0 if (pos+neg)==0 else (pos-neg)/max(1,(pos+neg))
    keywords = list(set(re.findall(r"\b\w{4,}\b", tl)))[:10]
    return {
        "entities": entities,
        "classification": {"category": best_cat, "confidence": min(0.95, 0.3 + 0.1*len(entities) + 0.05*len(keywords))},
        "sentiment": {"score": sent},
        "keywords": keywords,
        "language": "ru",
    }

@app.post("/v1/embeddings")
async def embeddings(payload: EmbeddingsPayload):
    inputs = payload.input
    if isinstance(inputs, str):
        inputs = [inputs]
    data = []
    for idx, inp in enumerate(inputs):
        emb = hash_embedding(inp)
        data.append({"object": "embedding", "index": idx, "embedding": emb})
    return {"object": "list", "data": data, "model": payload.model or "mock-embedding"}

@app.post("/v1/chat/completions")
async def chat_completions(body: Dict[str, Any]):
    # минимальный ответ, чтобы не падало
    return {
        "id": "mock-chat-1",
        "object": "chat.completion",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "Краткий ответ по базе знаний."}, "finish_reason": "stop"}
        ],
        "model": "mock-chat",
    }
