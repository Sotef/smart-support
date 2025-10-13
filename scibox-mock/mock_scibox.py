#!/usr/bin/env python3
"""
Mock Scibox API для демонстрации интеграции
Эмулирует работу системы глубокого обучения Scibox
"""

import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re
import random

app = FastAPI(
    title="Scibox Mock API",
    description="Эмуляция системы глубокого обучения Scibox",
    version="1.0.0"
)

class AnalyzeRequest(BaseModel):
    text: str
    operations: List[str] = ["entity_extraction", "text_classification", "sentiment_analysis"]

class Entity(BaseModel):
    text: str
    type: str
    confidence: float
    start: int
    end: int

class Classification(BaseModel):
    category: str
    confidence: float

class Sentiment(BaseModel):
    score: float
    label: str

class AnalyzeResponse(BaseModel):
    entities: List[Entity]
    classification: Classification
    sentiment: Sentiment
    keywords: List[str]
    language: str

class MockScibox:
    """Эмулятор Scibox API"""
    
    def __init__(self):
        # Паттерны для извлечения сущностей
        self.entity_patterns = {
            "phone": r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "account_number": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "amount": r'\b\d+[\s,.]?\d*\s*(руб|рублей|₽|р\.)\b',
            "date": r'\b\d{1,2}[.-]\d{1,2}[.-]\d{2,4}\b',
            "error_code": r'\b[Ee]rror\s*[-:]?\s*\d+\b|\b\d{3,4}\s*[Ee]rror\b'
        }
        
        # Ключевые слова для классификации
        self.classification_keywords = {
            "technical": [
                "ошибка", "не работает", "проблема", "сбой", "баг", "техническая поддержка",
                "не загружается", "зависает", "медленно", "error", "bug"
            ],
            "billing": [
                "счет", "платеж", "оплата", "деньги", "списание", "возврат", 
                "тариф", "абонентская плата", "биллинг", "счет-фактура"
            ],
            "account": [
                "аккаунт", "профиль", "регистрация", "вход", "пароль", 
                "логин", "восстановление", "блокировка", "доступ"
            ],
            "complaint": [
                "жалоба", "недоволен", "плохо", "ужасно", "возмущен",
                "претензия", "некачественно", "негативный опыт"
            ],
            "feature_request": [
                "хочу", "добавьте", "можно ли", "предлагаю", "улучшение",
                "новая функция", "функционал", "возможность"
            ]
        }

    async def extract_entities(self, text: str) -> List[Entity]:
        """Извлечение сущностей из текста"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                entity = Entity(
                    text=match.group(),
                    type=entity_type,
                    confidence=random.uniform(0.7, 0.95),
                    start=match.start(),
                    end=match.end()
                )
                entities.append(entity)
        
        return entities

    async def classify_text(self, text: str) -> Classification:
        """Классификация текста"""
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in self.classification_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[category] = score
        
        if not scores or max(scores.values()) == 0:
            category = "general"
            confidence = 0.5
        else:
            category = max(scores, key=scores.get)
            max_score = scores[category]
            confidence = min(0.95, 0.4 + max_score * 0.1)
        
        return Classification(
            category=category,
            confidence=confidence
        )

    async def analyze_sentiment(self, text: str) -> Sentiment:
        """Анализ тональности"""
        text_lower = text.lower()
        
        positive_words = [
            "хорошо", "отлично", "спасибо", "благодарен", "довольен", 
            "нравится", "классно", "супер"
        ]
        negative_words = [
            "плохо", "ужасно", "недоволен", "проблема", "ошибка", 
            "не работает", "жалоба", "возмущен", "кошмар"
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count + negative_count == 0:
            score = 0.0
            label = "neutral"
        else:
            score = (positive_count - negative_count) / (positive_count + negative_count)
            if score > 0.3:
                label = "positive"
            elif score < -0.3:
                label = "negative"
            else:
                label = "neutral"
        
        return Sentiment(score=score, label=label)

    async def extract_keywords(self, text: str) -> List[str]:
        """Извлечение ключевых слов"""
        words = re.findall(r'\b\w{4,}\b', text.lower())
        
        stop_words = {
            "который", "которая", "которое", "которые", "этот", "этого", "этой",
            "здравствуйте", "пожалуйста", "спасибо", "очень", "может", "можно"
        }
        
        keywords = [word for word in words if word not in stop_words]
        return list(set(keywords))[:10]

    async def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """Полный анализ текста"""
        # Добавляем небольшую задержку для имитации обработки
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        entities = []
        classification = Classification(category="general", confidence=0.5)
        sentiment = Sentiment(score=0.0, label="neutral")
        keywords = []
        
        if "entity_extraction" in request.operations:
            entities = await self.extract_entities(request.text)
        
        if "text_classification" in request.operations:
            classification = await self.classify_text(request.text)
        
        if "sentiment_analysis" in request.operations:
            sentiment = await self.analyze_sentiment(request.text)
        
        keywords = await self.extract_keywords(request.text)
        
        return AnalyzeResponse(
            entities=entities,
            classification=classification,
            sentiment=sentiment,
            keywords=keywords,
            language="ru"
        )

# Глобальный экземпляр эмулятора
mock_scibox = MockScibox()

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "Scibox Mock API",
        "version": "1.0.0"
    }

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest):
    """
    Анализ текста с извлечением сущностей, классификацией и анализом тональности
    """
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Текст не может быть пустым")
        
        result = await mock_scibox.analyze(request)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@app.get("/api/info")
async def get_info():
    """Информация о сервисе"""
    return {
        "name": "Scibox Mock API",
        "description": "Эмуляция системы глубокого обучения Scibox для Smart Support",
        "supported_operations": [
            "entity_extraction",
            "text_classification", 
            "sentiment_analysis"
        ],
        "supported_entity_types": list(mock_scibox.entity_patterns.keys()),
        "supported_categories": list(mock_scibox.classification_keywords.keys())
    }

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Scibox Mock API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "mock_scibox:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )