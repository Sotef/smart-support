from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv, find_dotenv

from .models import SupportRequest, SupportResponse, AnalysisResult
from .services.scibox_service import SciboxService
from .services.knowledge_base import KnowledgeBaseService
from .services.recommendation_engine import RecommendationEngine
from .services.vector_index import VectorIndex
from .database import get_db
from .websocket_manager import WebSocketManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env при старте процесса (если файл присутствует)
try:
    _env_path = find_dotenv(usecwd=True)
    if _env_path:
        load_dotenv(_env_path, override=True)
        logger.info(".env loaded from %s", _env_path)
    else:
        load_dotenv(override=True)
        logger.info(".env loaded (default search)")
except Exception as _e:
    logger.warning(".env load error: %s", _e)

app = FastAPI(
    title="Smart Support: ИИ-ассистент службы поддержки",
    description="Система анализа запросов поддержки с интеграцией Scibox",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")
# Путь для Vite-артефактов из сборки (assets/*)
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

# Инициализация сервисов
_scibox_url = os.getenv("SCIBOX_URL", "http://localhost:8001")
scibox_service = SciboxService(scibox_url=_scibox_url)
knowledge_base = KnowledgeBaseService()
recommendation_engine = RecommendationEngine(knowledge_base, scibox_service)
websocket_manager = WebSocketManager()

# Простой трекер тикетов/статистики (in-memory)
class TicketTracker:
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self.threshold = int(os.getenv("ESCALATE_THRESHOLD", "3"))

    def _get(self, client_id: str) -> Dict[str, Any]:
        if client_id not in self._data:
            self._data[client_id] = {
                "resolved": 0,
                "unresolved": 0,
                "consecutive_unresolved": 0,
                "history": [],
            }
        return self._data[client_id]

    def mark(self, client_id: str, request_id: str, resolved: bool) -> Dict[str, Any]:
        info = self._get(client_id)
        info["history"].append({"request_id": request_id, "resolved": resolved})
        if resolved:
            info["resolved"] += 1
            info["consecutive_unresolved"] = 0
        else:
            info["unresolved"] += 1
            info["consecutive_unresolved"] += 1
        return {
            "resolved": info["resolved"],
            "unresolved": info["unresolved"],
            "consecutive_unresolved": info["consecutive_unresolved"],
            "threshold": self.threshold,
            "should_escalate": info["consecutive_unresolved"] >= self.threshold,
        }

    def stats(self, client_id: str) -> Dict[str, Any]:
        info = self._get(client_id)
        return {
            "resolved": info["resolved"],
            "unresolved": info["unresolved"],
            "consecutive_unresolved": info["consecutive_unresolved"],
            "threshold": self.threshold,
        }


ticket_tracker = TicketTracker()

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Запуск Smart Support системы...")
    await knowledge_base.initialize()
    await scibox_service.initialize()
    # Загрузка векторного индекса, если есть
    try:
        recommendation_engine.load_vector_index()
    except Exception:
        pass
    logger.info("Система успешно запущена")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Главная страница"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/vite.svg")
async def vite_svg():
    """Статический ресурс иконки Vite из сборки"""
    return FileResponse("static/vite.svg")

@app.post("/api/analyze", response_model=SupportResponse)
async def analyze_support_request(request: SupportRequest):
    """
    Анализ запроса поддержки через Scibox
    """
    try:
        logger.info(f"Получен запрос: {request.text[:100]}...")
        
        # 1. Анализ через Scibox для извлечения сущностей и классификации
        analysis_result = await scibox_service.analyze_text(request.text)
        
        # 2. Поиск в базе знаний и генерация рекомендаций
        recommendations = await recommendation_engine.generate_recommendations(
            request.text,
            analysis_result
        )

        # 2.1 Согласование категории с базой знаний (если доступна однозначная категория)
        try:
            kb_cat = recommendations.get("kb_category")
            if kb_cat:
                from .models import RequestCategory as _RC
                analysis_result.classification = _RC(kb_cat)
        except Exception:
            pass
        
        # 2.2 Генеративный ответ (RAG) по запросу
        reply_mode = (request.metadata or {}).get("reply_mode") if isinstance(request.metadata, dict) else None
        if not reply_mode:
            import os
            reply_mode = os.getenv("REPLY_MODE", "kb")  # kb | gen
        generated_answer = None
        if reply_mode == "gen":
            rel_articles = recommendations.get("relevant_articles", [])
            generated_answer = await scibox_service.generate_answer_from_kb(request.text, rel_articles)

        # 3. Формирование ответа
        suggested = recommendations.get("responses", [])
        # Дословный ответ из БЗ (первый релевантный контент)
        kb_articles = recommendations.get("relevant_articles", [])
        if reply_mode != "gen" and kb_articles:
            kb_exact = (kb_articles[0].get("content") or "").strip()
            if kb_exact:
                suggested = [kb_exact] + suggested
        if generated_answer:
            suggested = [generated_answer] + suggested
        # Удалим дубликаты, сохранив порядок
        _seen = set()
        _uniq = []
        for s in suggested:
            key = (s or "").strip()
            if key and key not in _seen:
                _uniq.append(s)
                _seen.add(key)
        suggested = _uniq
        # Тональность (ярлык)
        tone = None
        if analysis_result.sentiment is not None:
            if analysis_result.sentiment > 0.3:
                tone = "positive"
            elif analysis_result.sentiment < -0.3:
                tone = "negative"
            else:
                tone = "neutral"

        # Категория/подкатегория из БЗ
        kb_cat = None
        kb_sub = None
        if kb_articles:
            kb_cat = kb_articles[0].get("main_category") or kb_articles[0].get("category")
            kb_sub = kb_articles[0].get("subcategory")

        # Ограничим до 3х ответов для UI
        suggested = suggested[:3]

        response = SupportResponse(
            request_id=request.request_id,
            classification=analysis_result.classification,
            entities=analysis_result.entities,
            confidence=analysis_result.confidence,
            sentiment_score=analysis_result.sentiment,
            tone_label=tone,
            kb_category=kb_cat,
            kb_subcategory=kb_sub,
            recommendations=recommendations,
            suggested_responses=suggested
        )
        
        # 4. Отправка через WebSocket для real-time обновлений
        await websocket_manager.broadcast({
            "type": "analysis_complete",
            "data": response.dict()
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Ошибка анализа: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@app.post("/api/feedback")
async def submit_feedback(feedback: Dict[str, Any]):
    """
    Получение обратной связи для улучшения рекомендаций
    """
    try:
        await recommendation_engine.process_feedback(feedback)
        return {"status": "success", "message": "Обратная связь получена"}
    except Exception as e:
        logger.error(f"Ошибка обработки обратной связи: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка обработки обратной связи")

@app.get("/api/knowledge-base/search")
async def search_knowledge_base(query: str, limit: int = 10):
    """
    Поиск в базе знаний
    """
    try:
        results = await knowledge_base.search(query, limit)
        return {"results": results}
    except Exception as e:
        logger.error(f"Ошибка поиска: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка поиска в базе знаний")

@app.get("/api/knowledge-base/article/{article_id}")
async def get_kb_article(article_id: str):
    try:
        article = await knowledge_base.get_article_by_id(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        return article.dict()
    except Exception as e:
        logger.error(f"Ошибка получения статьи: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения статьи")

# Векторный индекс КБ: rebuild / upsert / search
@app.post("/api/kb/embeddings/rebuild")
async def kb_embeddings_rebuild():
    try:
        articles = knowledge_base.articles
        ids = [a.id for a in articles]
        texts = [(a.title or "") + "\n" + (a.content or "") for a in articles]
        vecs = await scibox_service.embed_texts(texts)
        model = os.getenv("SCIBOX_EMBED_MODEL", os.getenv("MODEL_EMBED", "bge-m3"))
        path = os.getenv("VECTOR_INDEX_PATH", "data/kb_index.json")
        vi = VectorIndex(path)
        vi.save(model=model, dim=len(vecs[0]) if vecs else 0, ids=ids, vectors=vecs)
        # Перезагружаем в движке
        recommendation_engine.load_vector_index()
        return {"status": "ok", "count": len(ids), "dim": vi.dim, "model": model}
    except Exception as e:
        logger.error(f"kb_embeddings_rebuild error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка пересборки индекса")

@app.post("/api/kb/embeddings/upsert")
async def kb_embeddings_upsert(payload: Dict[str, Any]):
    try:
        art_id = str(payload.get("id") or payload.get("article_id"))
        if not art_id:
            raise HTTPException(status_code=400, detail="id required")
        article = await knowledge_base.get_article_by_id(art_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        txt = (article.title or "") + "\n" + (article.content or "")
        vec = (await scibox_service.embed_texts([txt]))[0]
        path = os.getenv("VECTOR_INDEX_PATH", "data/kb_index.json")
        vi = VectorIndex(path)
        if not vi.load():
            # если индекса нет — создаём новый
            model = os.getenv("SCIBOX_EMBED_MODEL", os.getenv("MODEL_EMBED", "bge-m3"))
            vi.save(model=model, dim=len(vec), ids=[art_id], vectors=[vec])
        else:
            vi.add_or_update(art_id, vec)
        recommendation_engine.load_vector_index()
        return {"status": "ok", "id": art_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"kb_embeddings_upsert error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка upsert индекса")

@app.get("/api/kb/embeddings/search")
async def kb_embeddings_search(query: str, k: int = 5):
    try:
        qv = (await scibox_service.embed_texts([query]))[0]
        path = os.getenv("VECTOR_INDEX_PATH", "data/kb_index.json")
        vi = VectorIndex(path)
        if not vi.load():
            return {"results": []}
        results = vi.search(qv, top_k=max(1, min(k, 20)))
        return {"results": [{"id": _id, "score": score} for _id, score in results]}
    except Exception as e:
        logger.error(f"kb_embeddings_search error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка поиска по эмбеддингам")

@app.post("/api/ticket/mark")
async def ticket_mark(payload: Dict[str, Any]):
    try:
        client_id = str(payload.get("client_id") or "default")
        request_id = str(payload.get("request_id") or "")
        resolved = bool(payload.get("resolved"))
        stats = ticket_tracker.mark(client_id, request_id, resolved)
        if stats["should_escalate"]:
            await websocket_manager.send_personal_message({
                "type": "escalate_suggested",
                "reason": "consecutive_unresolved",
                "stats": stats,
            }, client_id)
        return {"status": "ok", "stats": stats}
    except Exception as e:
        logger.error(f"ticket_mark error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка отметки статуса")

@app.get("/api/ticket/stats")
async def ticket_stats(client_id: str = "default"):
    try:
        return ticket_tracker.stats(client_id)
    except Exception as e:
        logger.error(f"ticket_stats error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка статуса")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket соединение для real-time уведомлений
    """
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message["type"] == "analyze_request":
                # Асинхронный анализ запроса
                asyncio.create_task(
                    analyze_and_notify(message["data"], client_id)
                )
                
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)

async def analyze_and_notify(request_data: Dict, client_id: str):
    """
    Асинхронный анализ и уведомление клиента
    """
    try:
        request = SupportRequest(**request_data)
        response = await analyze_support_request(request)
        
        await websocket_manager.send_personal_message({
            "type": "analysis_result",
            "data": response.dict()
        }, client_id)
        
    except Exception as e:
        logger.error(f"Ошибка асинхронного анализа: {str(e)}")
        await websocket_manager.send_personal_message({
            "type": "error",
            "message": str(e)
        }, client_id)

@app.get("/health")
async def health_check():
    """
    Проверка здоровья системы
    """
    return {
        "status": "healthy",
        "services": {
            "scibox": await scibox_service.health_check(),
            "knowledge_base": await knowledge_base.health_check()
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)