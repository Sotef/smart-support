import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..models import AnalysisResult, RequestCategory, FeedbackData
from .knowledge_base import KnowledgeBaseService
from .scibox_service import SciboxService

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Движок рекомендаций для генерации подсказок операторам
    """
    
    def __init__(self, knowledge_base: KnowledgeBaseService, scibox_service: SciboxService):
        self.knowledge_base = knowledge_base
        self.scibox_service = scibox_service
        self.feedback_data = []  # Хранилище для обратной связи
        
    async def generate_recommendations(self, text: str, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """
        Генерация рекомендаций на основе анализа текста
        """
        try:
            recommendations = {
                "category": analysis_result.classification.value,
                "confidence": analysis_result.confidence,
                "entities": [entity.dict() for entity in analysis_result.entities],
                "sentiment": analysis_result.sentiment,
                "keywords": analysis_result.keywords
            }
            
            # 1. Поиск релевантных статей в базе знаний
            relevant_articles = await self._find_relevant_articles(text, analysis_result)
            recommendations["relevant_articles"] = relevant_articles
            
            # 2. Генерация рекомендуемых ответов
            suggested_responses = await self._generate_suggested_responses(analysis_result)
            recommendations["responses"] = suggested_responses
            
            # 3. Определение действий для оператора
            actions = await self._determine_actions(analysis_result)
            recommendations["actions"] = actions
            
            # 4. Приоритетизация обращения
            priority = self._determine_priority(analysis_result)
            recommendations["priority"] = priority
            
            # 5. Дополнительные инсайты
            insights = await self._generate_insights(analysis_result)
            recommendations["insights"] = insights
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {str(e)}")
            return {"error": f"Ошибка генерации рекомендаций: {str(e)}"}

    async def _find_relevant_articles(self, text: str, analysis_result: AnalysisResult) -> List[Dict[str, Any]]:
        """
        Поиск релевантных статей в базе знаний
        """
        try:
            # Поиск по тексту запроса
            text_results = await self.knowledge_base.search(text, limit=3)
            
            # Поиск по ключевым словам
            keyword_results = []
            for keyword in analysis_result.keywords[:3]:
                keyword_results.extend(await self.knowledge_base.search(keyword, limit=2))
            
            # Поиск по категории
            category_articles = await self.knowledge_base.get_category_articles(analysis_result.classification)
            category_results = [
                {
                    "id": article.id,
                    "title": article.title,
                    "content": article.content,
                    "category": article.category.value,
                    "tags": article.tags,
                    "relevance_score": 0.8
                }
                for article in category_articles[:2]
            ]
            
            # Объединяем и убираем дубликаты
            all_results = text_results + keyword_results + category_results
            unique_results = []
            seen_ids = set()
            
            for result in all_results:
                if result["id"] not in seen_ids:
                    unique_results.append(result)
                    seen_ids.add(result["id"])
            
            # Сортируем по релевантности
            unique_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            return unique_results[:5]
            
        except Exception as e:
            logger.error(f"Ошибка поиска релевантных статей: {str(e)}")
            return []

    async def _generate_suggested_responses(self, analysis_result: AnalysisResult) -> List[str]:
        """
        Генерация предлагаемых ответов
        """
        try:
            base_responses = await self.knowledge_base.get_recommended_responses(analysis_result.classification)
            
            # Адаптируем ответы на основе анализа
            adapted_responses = []
            
            for response in base_responses:
                # Модифицируем ответ на основе тональности
                if analysis_result.sentiment and analysis_result.sentiment < -0.3:
                    # Негативная тональность - добавляем извинения
                    if "извинения" not in response.lower():
                        response = f"Приносим извинения за неудобства. {response}"
                
                adapted_responses.append(response)
            
            # Добавляем персонализированные ответы на основе сущностей
            if analysis_result.entities:
                entity_response = self._generate_entity_based_response(analysis_result.entities)
                if entity_response:
                    adapted_responses.insert(0, entity_response)
            
            return adapted_responses[:3]  # Возвращаем максимум 3 варианта
            
        except Exception as e:
            logger.error(f"Ошибка генерации ответов: {str(e)}")
            return ["Спасибо за обращение. Мы рассмотрим ваш вопрос."]

    def _generate_entity_based_response(self, entities) -> str:
        """
        Генерация ответа на основе извлеченных сущностей
        """
        entity_types = [entity.type.value for entity in entities]
        
        if "phone" in entity_types:
            return "Благодарим за предоставленный номер телефона. Мы свяжемся с вами для уточнения деталей."
        elif "email" in entity_types:
            return "Направим подробную информацию на указанный email адрес."
        elif "account_number" in entity_types:
            return "Проверим информацию по указанному номеру счета и предоставим детальный отчет."
        elif "amount" in entity_types:
            return "Уточним информацию по указанной сумме и предоставим разъяснения."
        
        return ""

    async def _determine_actions(self, analysis_result: AnalysisResult) -> List[str]:
        """
        Определение рекомендуемых действий для оператора
        """
        actions = []
        
        # Действия на основе категории
        category_actions = {
            RequestCategory.TECHNICAL: [
                "Создать тикет для технической поддержки",
                "Проверить статус системы",
                "Запросить дополнительную техническую информацию"
            ],
            RequestCategory.BILLING: [
                "Проверить историю платежей",
                "Связаться с финансовым отделом",
                "Запросить документы об оплате"
            ],
            RequestCategory.ACCOUNT: [
                "Инициировать процедуру восстановления доступа",
                "Запросить документы для верификации",
                "Проверить статус аккаунта в системе"
            ],
            RequestCategory.COMPLAINT: [
                "Зарегистрировать жалобу в системе",
                "Уведомить руководство",
                "Назначить ответственного за расследование"
            ],
            RequestCategory.FEATURE_REQUEST: [
                "Зафиксировать запрос в backlog",
                "Передать информацию команде разработки",
                "Оценить техническую возможность"
            ]
        }
        
        actions.extend(category_actions.get(analysis_result.classification, []))
        
        # Дополнительные действия на основе тональности
        if analysis_result.sentiment and analysis_result.sentiment < -0.5:
            actions.insert(0, "Приоритетная обработка - негативная тональность")
        
        # Действия на основе сущностей
        if analysis_result.entities:
            for entity in analysis_result.entities:
                if entity.type.value == "error_code":
                    actions.append(f"Проверить ошибку: {entity.text}")
                elif entity.type.value == "account_number":
                    actions.append(f"Проверить аккаунт: {entity.text}")
        
        return actions[:5]  # Максимум 5 действий

    def _determine_priority(self, analysis_result: AnalysisResult) -> str:
        """
        Определение приоритета обращения
        """
        # Высокий приоритет для жалоб с негативной тональностью
        if (analysis_result.classification == RequestCategory.COMPLAINT and 
            analysis_result.sentiment and analysis_result.sentiment < -0.5):
            return "HIGH"
        
        # Высокий приоритет для технических проблем с ошибками
        if (analysis_result.classification == RequestCategory.TECHNICAL and
            any(entity.type.value == "error_code" for entity in analysis_result.entities)):
            return "HIGH"
        
        # Средний приоритет для биллинговых вопросов
        if analysis_result.classification == RequestCategory.BILLING:
            return "MEDIUM"
        
        # Низкий приоритет для общих вопросов
        if analysis_result.classification == RequestCategory.GENERAL:
            return "LOW"
        
        return "MEDIUM"

    async def _generate_insights(self, analysis_result: AnalysisResult) -> List[str]:
        """
        Генерация дополнительных инсайтов
        """
        insights = []
        
        # Инсайт по уверенности
        if analysis_result.confidence < 0.6:
            insights.append(f"⚠️ Низкая уверенность классификации ({analysis_result.confidence:.2f}). Требуется ручная проверка.")
        
        # Инсайт по тональности
        if analysis_result.sentiment:
            if analysis_result.sentiment < -0.3:
                insights.append("😟 Негативная тональность. Требуется деликатное обращение.")
            elif analysis_result.sentiment > 0.3:
                insights.append("😊 Позитивная тональность. Клиент настроен благожелательно.")
        
        # Инсайт по количеству сущностей
        entity_count = len(analysis_result.entities)
        if entity_count == 0:
            insights.append("ℹ️ Сущности не обнаружены. Запрос может быть общим.")
        elif entity_count > 3:
            insights.append("📋 Много деталей в запросе. Внимательно обработайте всю информацию.")
        
        # Инсайт по ключевым словам
        if len(analysis_result.keywords) > 5:
            insights.append("🔍 Сложный запрос с множеством ключевых слов.")
        
        return insights

    async def process_feedback(self, feedback: Dict[str, Any]) -> bool:
        """
        Обработка обратной связи для улучшения рекомендаций
        """
        try:
            feedback_data = FeedbackData(**feedback)
            self.feedback_data.append(feedback_data)
            
            # В реальной системе здесь была бы логика обновления ML модели
            logger.info(f"Получена обратная связь для запроса {feedback_data.request_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки обратной связи: {str(e)}")
            return False

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик производительности системы
        """
        if not self.feedback_data:
            return {"status": "no_data", "message": "Недостаточно данных для анализа"}
        
        total_feedback = len(self.feedback_data)
        avg_quality = sum(fb.recommendation_quality for fb in self.feedback_data) / total_feedback
        response_usage = sum(1 for fb in self.feedback_data if fb.response_used) / total_feedback
        
        return {
            "total_feedback": total_feedback,
            "avg_recommendation_quality": round(avg_quality, 2),
            "response_usage_rate": round(response_usage * 100, 1),
            "last_feedback": self.feedback_data[-1].timestamp.isoformat() if self.feedback_data else None
        }