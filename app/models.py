from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class RequestCategory(str, Enum):
    """Категории запросов поддержки"""
    TECHNICAL = "technical"
    BILLING = "billing" 
    GENERAL = "general"
    COMPLAINT = "complaint"
    FEATURE_REQUEST = "feature_request"
    ACCOUNT = "account"

class Priority(str, Enum):
    """Приоритеты запросов"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EntityType(str, Enum):
    """Типы извлеченных сущностей"""
    PERSON = "person"
    PHONE = "phone"
    EMAIL = "email"
    ACCOUNT_NUMBER = "account_number"
    AMOUNT = "amount"
    DATE = "date"
    PRODUCT = "product"
    ERROR_CODE = "error_code"
    ADDRESS = "address"

class Entity(BaseModel):
    """Извлеченная сущность"""
    text: str = Field(..., description="Текст сущности")
    type: EntityType = Field(..., description="Тип сущности")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность в извлечении")
    start_pos: int = Field(..., description="Начальная позиция в тексте")
    end_pos: int = Field(..., description="Конечная позиция в тексте")

class SupportRequest(BaseModel):
    """Запрос в службу поддержки"""
    request_id: str = Field(..., description="ID запроса")
    text: str = Field(..., min_length=1, description="Текст запроса")
    customer_id: Optional[str] = Field(None, description="ID клиента")
    channel: str = Field(default="web", description="Канал обращения (web, phone, email)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время создания")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные")

class AnalysisResult(BaseModel):
    """Результат анализа через Scibox"""
    classification: RequestCategory = Field(..., description="Классификация запроса")
    entities: List[Entity] = Field(default_factory=list, description="Извлеченные сущности")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Общая уверенность анализа")
    sentiment: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Тональность")
    language: str = Field(default="ru", description="Язык текста")
    keywords: List[str] = Field(default_factory=list, description="Ключевые слова")

class KnowledgeBaseArticle(BaseModel):
    """Статья базы знаний"""
    id: str = Field(..., description="ID статьи")
    title: str = Field(..., description="Заголовок")
    content: str = Field(..., description="Содержание")
    category: RequestCategory = Field(..., description="Категория")
    tags: List[str] = Field(default_factory=list, description="Теги")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Релевантность")
    last_updated: datetime = Field(default_factory=datetime.now, description="Последнее обновление")

class Recommendation(BaseModel):
    """Рекомендация для оператора"""
    type: str = Field(..., description="Тип рекомендации")
    title: str = Field(..., description="Заголовок рекомендации")
    content: str = Field(..., description="Содержание рекомендации")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность в рекомендации")
    priority: Priority = Field(default=Priority.MEDIUM, description="Приоритет")
    actions: Optional[List[str]] = Field(None, description="Предлагаемые действия")

class SupportResponse(BaseModel):
    """Ответ системы с анализом и рекомендациями"""
    request_id: str = Field(..., description="ID исходного запроса")
    classification: RequestCategory = Field(..., description="Классификация запроса")
    entities: List[Entity] = Field(default_factory=list, description="Извлеченные сущности")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Общая уверенность анализа")
    
    recommendations: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Рекомендации из базы знаний"
    )
    suggested_responses: List[str] = Field(
        default_factory=list, 
        description="Предлагаемые ответы"
    )
    
    relevant_articles: List[KnowledgeBaseArticle] = Field(
        default_factory=list, 
        description="Релевантные статьи базы знаний"
    )
    
    processing_time: Optional[float] = Field(None, description="Время обработки в секундах")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время ответа")

class FeedbackData(BaseModel):
    """Обратная связь по качеству рекомендаций"""
    request_id: str = Field(..., description="ID запроса")
    recommendation_quality: int = Field(..., ge=1, le=5, description="Качество рекомендаций (1-5)")
    response_used: bool = Field(..., description="Был ли использован предложенный ответ")
    response_effectiveness: Optional[int] = Field(None, ge=1, le=5, description="Эффективность ответа")
    operator_comments: Optional[str] = Field(None, description="Комментарии оператора")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время фидбека")

class SystemStats(BaseModel):
    """Статистика работы системы"""
    total_requests: int = Field(default=0, description="Общее количество запросов")
    avg_processing_time: float = Field(default=0.0, description="Среднее время обработки")
    accuracy_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Точность классификации")
    most_common_categories: Dict[str, int] = Field(
        default_factory=dict, 
        description="Наиболее частые категории"
    )
    uptime: float = Field(default=0.0, description="Время работы системы")

class WebSocketMessage(BaseModel):
    """Сообщение для WebSocket"""
    type: str = Field(..., description="Тип сообщения")
    data: Optional[Dict[str, Any]] = Field(None, description="Данные сообщения")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время сообщения")
    client_id: Optional[str] = Field(None, description="ID клиента")