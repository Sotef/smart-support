from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import asyncio
import json
import logging
import os
from typing import List, Dict, Any

from dotenv import load_dotenv

from .models import SupportRequest, SupportResponse, AnalysisResult
from .services.scibox_service import SciboxService
from .services.knowledge_base import KnowledgeBaseService
from .services.recommendation_engine import RecommendationEngine
from .database import get_db
from .websocket_manager import WebSocketManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env при старте процесса (если файл присутствует)
load_dotenv()

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

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Запуск Smart Support системы...")
    await knowledge_base.initialize()
    await scibox_service.initialize()
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
        
        # 3. Формирование ответа
        response = SupportResponse(
            request_id=request.request_id,
            classification=analysis_result.classification,
            entities=analysis_result.entities,
            confidence=analysis_result.confidence,
            recommendations=recommendations,
            suggested_responses=recommendations.get("responses", [])
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