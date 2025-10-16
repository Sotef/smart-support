from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Body
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
from .database import get_db as get_db_placeholder
from .db import Base, engine, get_db
from .auth import router as auth_router
from .websocket_manager import WebSocketManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Доп. файл-логгер
try:
    import logging.handlers, pathlib
    pathlib.Path("logs").mkdir(parents=True, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler("logs/app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(fh)
    logger.info("File logging enabled at logs/app.log")
except Exception as _e:
    logger.warning("File logging init failed: %s", _e)

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

# Маршруты аутентификации
app.include_router(auth_router)

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
# Путь для Next.js export (_next/*)
app.mount("/_next", StaticFiles(directory="static/_next"), name="_next")

# Инициализация сервисов
_scibox_url = os.getenv("SCIBOX_URL", "http://localhost:8001")
scibox_service = SciboxService(scibox_url=_scibox_url)
knowledge_base = KnowledgeBaseService()
recommendation_engine = RecommendationEngine(knowledge_base, scibox_service)
websocket_manager = WebSocketManager()

# Переключатель сохранения логов (для тестов можно не сохранять)
SAVE_LOGS = os.getenv("SAVE_LOGS", "0").lower() in ("1", "true", "yes")

# In-memory Session Store
from datetime import datetime
from uuid import uuid4

class SessionStore:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create(self, client_id: str, subject: str, description: str) -> str:
        sid = f"S{int(datetime.utcnow().timestamp())}_{uuid4().hex[:6]}"
        self.sessions[sid] = {
            "id": sid,
            "client_id": client_id,
            "operator_id": None,
            "subject": subject,
            "status": "assigned",
            "created_at": datetime.utcnow(),
            "messages": [
                {
                    "id": f"m_{uuid4().hex[:8]}",
                    "sender": "client",
                    "text": description,
                    "timestamp": datetime.utcnow(),
                }
            ],
        }
        return sid

    def get(self, sid: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(sid)

    def list(self) -> List[Dict[str, Any]]:
        return list(self.sessions.values())

    def add_message(self, sid: str, sender: str, text: str, reply_to: Optional[str] = None) -> Dict[str, Any]:
        s = self.get(sid)
        if not s:
            raise KeyError("session not found")
        msg = {
            "id": f"m_{uuid4().hex[:8]}",
            "sender": sender,
            "text": text,
            "timestamp": datetime.utcnow(),
            "status": "sent",
            "read_by": [],
        }
        if reply_to:
            msg["replyTo"] = reply_to
        # Бот всегда "читает" клиентские сообщения
        if sender == "client":
            msg["read_by"].append("bot")
        s["messages"].append(msg)
        return msg

    def close(self, sid: str, resolved: bool):
        s = self.get(sid)
        if not s:
            raise KeyError("session not found")
        s["status"] = "solved" if resolved else "closed"
        s["closed_at"] = datetime.utcnow()
        return s

session_store = SessionStore()

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

def _ensure_user_columns():
    try:
        from sqlalchemy import text
        db_url = os.getenv("DATABASE_URL", "sqlite:///data/app.db")
        if db_url.startswith("sqlite"):
            with engine.connect() as conn:
                cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users)"))]
                to_add = []
                if 'name' not in cols:
                    to_add.append("ALTER TABLE users ADD COLUMN name VARCHAR(255)")
                if 'phone' not in cols:
                    to_add.append("ALTER TABLE users ADD COLUMN phone VARCHAR(64)")
                if 'corporate_code' not in cols:
                    to_add.append("ALTER TABLE users ADD COLUMN corporate_code VARCHAR(32)")
                if 'operator_number' not in cols:
                    to_add.append("ALTER TABLE users ADD COLUMN operator_number INTEGER")
                for stmt in to_add:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        pass
                # indices
                try:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_operator_number ON users(operator_number)"))
                except Exception:
                    pass
                try:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_corporate_code ON users(corporate_code)"))
                except Exception:
                    pass
                conn.commit()
                logger.info("Ensured users table columns/indexes")
    except Exception as e:
        logger.warning(f"ensure_user_columns error: {e}")

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Запуск Smart Support системы...")
    # Инициализируем БД и создаём таблицы (если нет)
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_user_columns()
        logger.info("Database initialized")
    except Exception as _e:
        logger.error(f"DB init error: {_e}")
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

@app.get("/api/health")
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

@app.get("/api/logs")
async def get_logs(lines: int = 100, level: str = None):
    """
    Получение последних строк из лог-файла
    
    - **lines**: количество последних строк (по умолчанию 100)
    - **level**: фильтр по уровню (INFO, WARNING, ERROR)
    """
    try:
        log_path = "logs/app.log"
        if not os.path.exists(log_path):
            return {"logs": [], "message": "Log file not found"}
        
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        # Получаем последние N строк
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Фильтрация по уровню, если указан
        if level:
            level_upper = level.upper()
            recent_lines = [line for line in recent_lines if level_upper in line]
        
        return {
            "logs": recent_lines,
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines)
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")

@app.get("/api/logs/tail")
async def get_logs_tail(lines: int = 50):
    """
    Получение последних строк логов в простом текстовом формате
    
    - **lines**: количество последних строк (по умолчанию 50)
    """
    from fastapi.responses import PlainTextResponse
    try:
        log_path = "logs/app.log"
        if not os.path.exists(log_path):
            return PlainTextResponse("Log file not found", status_code=404)
        
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return PlainTextResponse("".join(recent_lines))
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return PlainTextResponse(f"Error reading logs: {str(e)}", status_code=500)

# Критичные API endpoints - должны быть ПЕРЕД SPA fallback
@app.get("/api/session/list")
async def session_list():
    items = session_store.list()
    counts = {"assigned": 0, "started": 0, "solved": 0, "closed": 0}
    for it in items:
        st = it.get("status")
        if st in counts:
            counts[st] += 1
    return {"items": items, "counts": counts}

@app.get("/api/session/analytics")
async def session_analytics():
    """
    Аналитика сессий с категоризацией
    """
    sessions = session_store.list()
    analytics = []
    
    for s in sessions:
        # Получаем первое сообщение клиента
        client_msgs = [m for m in s.get("messages", []) if m.get("sender") == "client"]
        first_msg = client_msgs[0] if client_msgs else None
        
        # Анализируем первое сообщение для категоризации
        category = None
        sentiment = None
        keywords = []
        
        if first_msg:
            try:
                text = first_msg.get("text", "")
                analysis = await scibox_service.analyze_text(text)
                category = str(analysis.classification.value) if analysis.classification else None
                sentiment = analysis.sentiment
                keywords = analysis.keywords[:5] if analysis.keywords else []
            except Exception as e:
                logger.warning(f"Analytics analysis error: {e}")
        
        analytics.append({
            "session_id": s.get("id"),
            "subject": s.get("subject"),
            "status": s.get("status"),
            "created_at": s.get("created_at"),
            "client_question": first_msg.get("text") if first_msg else None,
            "category": category,
            "sentiment": sentiment,
            "keywords": keywords,
            "messages_count": len(s.get("messages", [])),
            "priority": s.get("priority"),
        })
    
    # Статистика по категориям
    category_stats = {}
    for item in analytics:
        cat = item.get("category") or "unknown"
        category_stats[cat] = category_stats.get(cat, 0) + 1
    
    return {
        "total_sessions": len(sessions),
        "sessions": analytics,
        "category_stats": category_stats
    }

@app.get("/api/session/{session_id}")
async def session_get(session_id: str):
    s = session_store.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s

# SPA fallback: обслуживаем index.html для любых путей, не начинающихся с API/статик  
# NOTE: Этот роут должен быть ПОСЛЕДНИМ, так как перехватывает все пути
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    # API роуты обрабатываются другими эндпоинтами - пропускаем
    if full_path.startswith("api/"):
        # Let FastAPI continue to other routes
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Статические ресурсы
    if full_path.startswith(("assets/", "static/", "_next/")):
        raise HTTPException(status_code=404, detail="Not Found")

    # Try Next.js static-export routes first: 
    # e.g. /operator -> static/operator.html, /login/client -> static/login/client.html
    candidate_files = []
    if full_path:
        candidate_files.append(f"static/{full_path}.html")
        candidate_files.append(f"static/{full_path}/index.html")
    # Fallback to root index.html
    candidate_files.append("static/index.html")

    for p in candidate_files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            continue
    raise HTTPException(status_code=404, detail="Not Found")

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
        # Индексируем формулировку вопроса (title) — а не ответ
        texts = [(a.title or "") for a in articles]
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
        # Индексируем только вопрос (title)
        txt = (article.title or "")
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

@app.post("/api/session/start")
async def session_start(payload: Dict[str, Any]):
    try:
        client_id = str(payload.get("client_id") or f"client_{uuid4().hex[:6]}")
        subject = (payload.get("subject") or "").strip() or "Вопрос"
        description = (payload.get("description") or "").strip()
        if not description:
            raise HTTPException(status_code=400, detail="description required")
        
        # Создаём сессию
        try:
            sid = session_store.create(client_id, subject, description)
        except Exception as e:
            logger.error(f"session_store.create error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")
        
        # Анализ первого сообщения и автоответ бота
        suggestions = []
        req = SupportRequest(
            request_id=f"req_{uuid4().hex[:8]}",
            text=description,
            channel="web",
            metadata={"reply_mode": "kb"},
        )
        try:
            resp: SupportResponse = await analyze_support_request(req)
            top = (resp.suggested_responses or [])[:1]
            if top:
                session_store.add_message(sid, "bot", top[0])
            suggestions = resp.suggested_responses or []
        except Exception as _e:
            logger.warning(f"session_start analyze fallback: {_e}", exc_info=True)
            # Добавляем дефолтное сообщение бота при ошибке анализа
            try:
                session_store.add_message(sid, "bot", "Здравствуйте! Ваш вопрос принят. Оператор ответит в ближайшее время.")
            except Exception:
                pass
        
        # RT уведомление для операторов о новой сессии
        try:
            await websocket_manager.broadcast({
                "type": "session_started",
                "session": session_store.get(sid)
            })
        except Exception as ws_e:
            logger.warning(f"websocket broadcast failed: {ws_e}")
        
        # Получаем актуальную сессию
        try:
            session = session_store.get(sid)
            if not session:
                raise Exception(f"Session {sid} not found after creation")
            
            return {
                "session_id": sid,
                "subject": subject,
                "status": session.get("status", "assigned"),
                "messages": session.get("messages", []),
                "suggested_responses": suggestions,
            }
        except Exception as e:
            logger.error(f"session_start get session error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Session created but failed to retrieve: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"session_start unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/api/message/send")
async def message_send(payload: Dict[str, Any]):
    try:
        sid = str(payload.get("session_id") or "")
        sender = str(payload.get("sender") or "")
        text = str(payload.get("text") or "").strip()
        reply_to = payload.get("reply_to")
        if not sid or not sender or not text:
            raise HTTPException(status_code=400, detail="session_id, sender, text required")
        s = session_store.get(sid)
        if not s:
            raise HTTPException(status_code=404, detail="session not found")
        msg = session_store.add_message(sid, sender, text, reply_to)

        # RT уведомление операторам о новом сообщении
        try:
            await websocket_manager.broadcast({
                "type": "message_created",
                "session_id": sid,
                "message": msg,
            })
        except Exception:
            pass

        suggestions: List[str] = []
        operator_requested = False
        escalate = False
        # Ключевые слова для вызова оператора
        kws = ["оператор", "человек", "живой", "сотрудник", "консультант"]
        if sender == "client":
            if any(k in text.lower() for k in kws):
                operator_requested = True
            # Подсчёт клиентских сообщений
            client_msgs = [m for m in s["messages"] if m.get("sender") == "client"]
            # Анализ и автоответ
            req = SupportRequest(
                request_id=f"req_{uuid4().hex[:8]}",
                text=text,
                channel="web",
                metadata={"reply_mode": "kb"},
            )
            try:
                resp: SupportResponse = await analyze_support_request(req)
                suggestions = (resp.suggested_responses or [])[:3]
                # Негативный тон до 3 вопросов — эскалация
                if len(client_msgs) <= 3 and (resp.sentiment_score or 0) < -0.3:
                    escalate = True
                # Приоритет сессии
                try:
                    s["priority"] = (resp.recommendations or {}).get("priority") or s.get("priority")
                except Exception:
                    pass
                # Логируем категории/тональность/приоритет
                try:
                    logger.info(f"msg_user sid={sid} cat={resp.kb_category or resp.classification} sub={resp.kb_subcategory} tone={resp.tone_label} priority={(resp.recommendations or {}).get('priority')}")
                except Exception:
                    pass
                # Автоответ бота после каждого сообщения клиента
                if suggestions:
                    session_store.add_message(sid, "bot", suggestions[0])
            except Exception as _e:
                logger.warning(f"message_send analyze fallback: {_e}")
                suggestions = []
            # Предложить подключение оператора после 3 вопросов
            if len(client_msgs) >= 3:
                operator_requested = True
            # Оповещение операторов по WS
            if escalate or operator_requested:
                try:
                    await websocket_manager.broadcast({
                        "type": "escalate_suggested",
                        "session_id": sid,
                        "reason": "sentiment" if escalate else "requested",
                    })
                except Exception:
                    pass
        else:
            # Сообщение от оператора: добавляем системное сообщение при первом присоединении
            operator_msgs = [m for m in s["messages"] if m.get("sender") == "operator"]
            if len(operator_msgs) == 1:  # Первое сообщение оператора (только что добавили)
                # Видно оператору — инструкция
                system_msg_op = "Процедура рассмотрения жалоб:\n1. Зафиксируйте жалобу в системе\n2. Уведомите клиента о регистрации\n3. Проведите расследование\n4. Предоставьте ответ в установленные сроки"
                s["messages"].append({
                    "id": f"m_{uuid4().hex[:8]}",
                    "sender": "system",
                    "text": system_msg_op,
                    "timestamp": datetime.utcnow(),
                    "visible_to": "operator",
                })
                # Видно клиенту — уведомление о присоединении оператора
                s["messages"].append({
                    "id": f"m_{uuid4().hex[:8]}",
                    "sender": "system",
                    "text": "Sys: Оператор присоединился",
                    "timestamp": datetime.utcnow(),
                    "visible_to": "client",
                })
                try:
                    await websocket_manager.broadcast({
                        "type": "message_created",
                        "session_id": sid,
                        "message": {"sender":"system","text":"Sys: Оператор присоединился"}
                    })
                except Exception:
                    pass
            # Предложить доп. ответы из анализа
            req = SupportRequest(
                request_id=f"req_{uuid4().hex[:8]}",
                text=text,
                channel="web",
                metadata={"reply_mode": "kb"},
            )
            try:
                resp: SupportResponse = await analyze_support_request(req)
                suggestions = (resp.suggested_responses or [])[:3]
            except Exception as _e:
                logger.warning(f"operator analyze fallback: {_e}")
                suggestions = []

        return {
            "session_id": sid,
            "messages": s["messages"],
            "suggested_responses": suggestions,
            "operator_requested": operator_requested,
            "escalate": escalate,
            "status": s["status"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"message_send error: {e}")
        raise HTTPException(status_code=500, detail="message_send failed")

@app.post("/api/session/close")
async def session_close(payload: Dict[str, Any]):
    try:
        sid = str(payload.get("session_id") or "")
        resolved = bool(payload.get("resolved"))
        if not sid:
            raise HTTPException(status_code=400, detail="session_id required")
        s = session_store.close(sid, resolved)
        return {"session_id": sid, "status": s["status"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"session_close error: {e}")
        raise HTTPException(status_code=500, detail="session_close failed")

# Эти эндпоинты перенесены выше SPA fallback

@app.post("/api/message/read")
async def message_read(payload: Dict[str, Any]):
    try:
        sid = str(payload.get("session_id") or "")
        reader = str(payload.get("reader") or "")  # client | operator | bot
        up_to_id = payload.get("up_to_id")
        if not sid or reader not in ("client","operator","bot"):
            raise HTTPException(status_code=400, detail="session_id, valid reader required")
        s = session_store.get(sid)
        if not s:
            raise HTTPException(status_code=404, detail="session not found")
        ids_marked = []
        for m in s["messages"]:
            if up_to_id and m["id"] == up_to_id:
                # mark this and all previous
                if reader not in m.get("read_by", []):
                    m.setdefault("read_by", []).append(reader)
                    ids_marked.append(m["id"])
                break
            # mark progressively (skip messages от самого reader)
            if m.get("sender") != reader:
                if reader not in m.get("read_by", []):
                    m.setdefault("read_by", []).append(reader)
                    ids_marked.append(m["id"])
        # WS уведомление о прочтении
        try:
            await websocket_manager.broadcast({
                "type": "message_read",
                "session_id": sid,
                "reader": reader,
                "message_ids": ids_marked,
            })
        except Exception:
            pass
        return {"session_id": sid, "reader": reader, "marked": ids_marked}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"message_read error: {e}")
        raise HTTPException(status_code=500, detail="message_read failed")

@app.post("/api/message/edit")
async def message_edit(payload: Dict[str, Any]):
    try:
        sid = str(payload.get("session_id") or "")
        mid = str(payload.get("message_id") or "")
        new_text = str(payload.get("new_text") or "").strip()
        if not sid or not mid or not new_text:
            raise HTTPException(status_code=400, detail="session_id, message_id, new_text required")
        s = session_store.get(sid)
        if not s:
            raise HTTPException(status_code=404, detail="session not found")
        for m in s["messages"]:
            if m["id"] == mid:
                hist = m.setdefault("editHistory", [])
                hist.append({"text": m["text"], "editedAt": datetime.utcnow().isoformat()})
                m["text"] = new_text
                m["edited"] = True
                break
        return {"session_id": sid, "messages": s["messages"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"message_edit error: {e}")
        raise HTTPException(status_code=500, detail="message_edit failed")

@app.post("/api/message/delete")
async def message_delete(payload: Dict[str, Any]):
    try:
        sid = str(payload.get("session_id") or "")
        mid = str(payload.get("message_id") or "")
        if not sid or not mid:
            raise HTTPException(status_code=400, detail="session_id, message_id required")
        s = session_store.get(sid)
        if not s:
            raise HTTPException(status_code=404, detail="session not found")
        for m in s["messages"]:
            if m["id"] == mid:
                m["deleted"] = True
                m["deletedAt"] = datetime.utcnow().isoformat()
                break
        return {"session_id": sid, "messages": s["messages"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"message_delete error: {e}")
        raise HTTPException(status_code=500, detail="message_delete failed")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
