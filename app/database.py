# Синтетическая база данных для демонстрации
# В реальной системе здесь был бы SQLAlchemy + PostgreSQL

import asyncio
from typing import Optional, Any

async def get_db():
    """
    Заглушка для dependency injection базы данных
    В реальной системе здесь был бы SQLAlchemy session
    """
    yield None

class SyntheticDatabase:
    """
    Синтетическая база данных для хранения данных приложения
    """
    
    def __init__(self):
        self.requests = {}
        self.feedback = {}
        self.users = {}
        
    async def save_request(self, request_data: dict) -> str:
        """Сохранение запроса"""
        request_id = request_data.get("request_id")
        self.requests[request_id] = request_data
        return request_id
        
    async def get_request(self, request_id: str) -> Optional[dict]:
        """Получение запроса по ID"""
        return self.requests.get(request_id)
        
    async def save_feedback(self, feedback_data: dict) -> bool:
        """Сохранение обратной связи"""
        request_id = feedback_data.get("request_id")
        self.feedback[request_id] = feedback_data
        return True
        
    async def get_feedback(self, request_id: str) -> Optional[dict]:
        """Получение обратной связи по ID запроса"""
        return self.feedback.get(request_id)

# Глобальная заглушка базы данных
synthetic_db = SyntheticDatabase()