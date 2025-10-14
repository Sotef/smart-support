import asyncio
import httpx
import json
import re
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models import AnalysisResult, Entity, EntityType, RequestCategory

logger = logging.getLogger(__name__)

class SciboxService:
    """
    Сервис интеграции с системой глубокого обучения Scibox
    Реализует извлечение именованных сущностей и классификацию текстов
    """
    
    def __init__(self, scibox_url: str = "http://localhost:8001", api_key: Optional[str] = None):
        self.scibox_url = scibox_url
        self.api_key = api_key or os.getenv("SCIBOX_API_KEY")
        self.client = None
        self.initialized = False
        
        # Паттерны для извлечения сущностей (как заглушка до интеграции с реальным Scibox)
        self.entity_patterns = {
            EntityType.PHONE: r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}',
            EntityType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            EntityType.ACCOUNT_NUMBER: r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            EntityType.AMOUNT: r'\b\d+[\s,.]?\d*\s*(руб|рублей|₽|р\.)\b',
            EntityType.DATE: r'\b\d{1,2}[.-]\d{1,2}[.-]\d{2,4}\b',
            EntityType.ERROR_CODE: r'\b[Ee]rror\s*[-:]?\s*\d+\b|\b\d{3,4}\s*[Ee]rror\b'
        }
        
        # Ключевые слова для классификации (синтетические данные)
        self.classification_keywords = {
            RequestCategory.TECHNICAL: [
                'ошибка', 'не работает', 'проблема', 'сбой', 'баг', 'техническая поддержка',
                'не загружается', 'зависает', 'медленно', 'error', 'bug'
            ],
            RequestCategory.BILLING: [
                'счет', 'платеж', 'оплата', 'деньги', 'списание', 'возврат', 
                'тариф', 'абонентская плата', 'биллинг', 'счет-фактура'
            ],
            RequestCategory.ACCOUNT: [
                'аккаунт', 'профиль', 'регистрация', 'вход', 'пароль', 
                'логин', 'восстановление', 'блокировка', 'доступ'
            ],
            RequestCategory.COMPLAINT: [
                'жалоба', 'недоволен', 'плохо', 'ужасно', 'возмущен',
                'претензия', 'некачественно', 'негативный опыт'
            ],
            RequestCategory.FEATURE_REQUEST: [
                'хочу', 'добавьте', 'можно ли', 'предлагаю', 'улучшение',
                'новая функция', 'функционал', 'возможность'
            ]
        }

    async def initialize(self):
        """Инициализация сервиса"""
        try:
            self.client = httpx.AsyncClient(timeout=30.0)
            
            # Проверяем доступность Scibox (в реальной интеграции)
            try:
                response = await self.client.get(f"{self.scibox_url}/health")
                if response.status_code == 200:
                    logger.info("Подключение к Scibox установлено")
                else:
                    logger.warning("Scibox недоступен, используем синтетические данные")
            except:
                logger.info("Работаем с синтетическими данными (Scibox не подключен)")
            
            self.initialized = True
            logger.info("SciboxService инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации SciboxService: {str(e)}")
            # Работаем с синтетическими данными
            self.initialized = True

    async def analyze_text(self, text: str) -> AnalysisResult:
        """
        Анализ текста через Scibox с извлечением сущностей и классификацией
        """
        try:
            # Попытка реальной интеграции с Scibox
            if self.client:
                try:
                    response = await self._call_scibox_api(text)
                    if response:
                        return response
                except Exception as e:
                    logger.warning(f"Ошибка вызова Scibox API: {str(e)}")
            
            # Fallback: синтетический анализ
            return await self._synthetic_analysis(text)
            
        except Exception as e:
            logger.error(f"Ошибка анализа текста: {str(e)}")
            # Возвращаем базовый результат
            return AnalysisResult(
                classification=RequestCategory.GENERAL,
                entities=[],
                confidence=0.5,
                sentiment=0.0,
                keywords=[]
            )

    async def _call_scibox_api(self, text: str) -> Optional[AnalysisResult]:
        """
        Вызов реального API Scibox (система глубокого обучения)
        """
        try:
            payload = {
                "text": text,
                "operations": [
                    "entity_extraction",  # Извлечение сущностей
                    "text_classification", # Классификация
                    "sentiment_analysis"   # Анализ тональности
                ]
            }
            
            headers = {}
            if self.api_key:
                # Передаем API-ключ как Bearer токен (при необходимости скорректировать согласно документации Scibox)
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = await self.client.post(
                f"{self.scibox_url}/api/analyze",
                json=payload,
                headers=headers or None,
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_scibox_response(data, text)
                
        except Exception as e:
            logger.error(f"Ошибка вызова Scibox API: {str(e)}")
            return None

    def _parse_scibox_response(self, data: Dict, original_text: str) -> AnalysisResult:
        """
        Парсинг ответа от Scibox в наш формат
        """
        entities = []
        
        # Парсим сущности из ответа Scibox
        for entity_data in data.get("entities", []):
            entity = Entity(
                text=entity_data.get("text", ""),
                type=EntityType(entity_data.get("type", "person")),
                confidence=entity_data.get("confidence", 0.0),
                start_pos=entity_data.get("start", 0),
                end_pos=entity_data.get("end", 0)
            )
            entities.append(entity)
        
        # Определяем категорию
        classification = RequestCategory(
            data.get("classification", {}).get("category", "general")
        )
        
        return AnalysisResult(
            classification=classification,
            entities=entities,
            confidence=data.get("classification", {}).get("confidence", 0.0),
            sentiment=data.get("sentiment", {}).get("score", 0.0),
            keywords=data.get("keywords", []),
            language=data.get("language", "ru")
        )

    async def _synthetic_analysis(self, text: str) -> AnalysisResult:
        """
        Синтетический анализ текста для демонстрации функционала
        """
        text_lower = text.lower()
        
        # 1. Извлечение сущностей с помощью регулярных выражений
        entities = self._extract_entities_regex(text)
        
        # 2. Классификация на основе ключевых слов
        classification = self._classify_text_keywords(text_lower)
        
        # 3. Простой анализ тональности
        sentiment = self._analyze_sentiment(text_lower)
        
        # 4. Извлечение ключевых слов
        keywords = self._extract_keywords(text_lower)
        
        # Общая уверенность на основе количества найденных признаков
        confidence = min(0.95, 0.3 + len(entities) * 0.1 + len(keywords) * 0.05)
        
        return AnalysisResult(
            classification=classification,
            entities=entities,
            confidence=confidence,
            sentiment=sentiment,
            keywords=keywords,
            language="ru"
        )

    def _extract_entities_regex(self, text: str) -> List[Entity]:
        """Извлечение сущностей с помощью регулярных выражений"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                entity = Entity(
                    text=match.group(),
                    type=entity_type,
                    confidence=0.8,  # Базовая уверенность для regex
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                entities.append(entity)
        
        return entities

    def _classify_text_keywords(self, text: str) -> RequestCategory:
        """Классификация на основе ключевых слов"""
        scores = {}
        
        for category, keywords in self.classification_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            scores[category] = score
        
        if not scores or max(scores.values()) == 0:
            return RequestCategory.GENERAL
        
        return max(scores, key=scores.get)

    def _analyze_sentiment(self, text: str) -> float:
        """Простой анализ тональности"""
        positive_words = [
            'хорошо', 'отлично', 'спасибо', 'благодарен', 'довольен', 
            'нравится', 'классно', 'супер'
        ]
        negative_words = [
            'плохо', 'ужасно', 'недоволен', 'проблема', 'ошибка', 
            'не работает', 'жалоба', 'возмущен', 'кошмар'
        ]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count + negative_count == 0:
            return 0.0
        
        sentiment = (positive_count - negative_count) / (positive_count + negative_count)
        return max(-1.0, min(1.0, sentiment))

    def _extract_keywords(self, text: str) -> List[str]:
        """Извлечение ключевых слов"""
        # Простое извлечение на основе частотности и длины слов
        words = re.findall(r'\b\w{4,}\b', text)
        
        # Убираем стоп-слова
        stop_words = {
            'который', 'которая', 'которое', 'которые', 'этот', 'этого', 'этой',
            'здравствуйте', 'пожалуйста', 'спасибо', 'очень', 'может', 'можно'
        }
        
        keywords = [word for word in words if word not in stop_words]
        
        # Возвращаем уникальные ключевые слова (максимум 10)
        return list(set(keywords))[:10]

    async def health_check(self) -> Dict[str, Any]:
        """Проверка состояния сервиса"""
        if not self.initialized:
            return {"status": "not_initialized", "message": "Сервис не инициализирован"}
        
        try:
            if self.client:
                response = await self.client.get(f"{self.scibox_url}/health")
                if response.status_code == 200:
                    return {"status": "connected", "message": "Подключен к Scibox"}
            
            return {"status": "synthetic", "message": "Работает с синтетическими данными"}
            
        except Exception as e:
            return {"status": "error", "message": f"Ошибка: {str(e)}"}

    async def close(self):
        """Закрытие соединений"""
        if self.client:
            await self.client.aclose()