import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..models import AnalysisResult, RequestCategory, FeedbackData
from .knowledge_base import KnowledgeBaseService
from .scibox_service import SciboxService
from .vector_index import VectorIndex

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Движок рекомендаций для генерации подсказок операторам
    """
    
    def __init__(self, knowledge_base: KnowledgeBaseService, scibox_service: SciboxService):
        self.knowledge_base = knowledge_base
        self.scibox_service = scibox_service
        self.feedback_data = []  # Хранилище для обратной связи
        # Embeddings конфигурация
        import os
        self.use_embeddings = os.getenv("USE_EMBEDDINGS", "true").lower() in ("1","true","yes")
        self.embed_cache: Dict[str, List[float]] = {}
        # Vector index
        self.vector_index_path = os.getenv("VECTOR_INDEX_PATH", "data/kb_index.json")
        self.vindex: Optional[VectorIndex] = None
        
    def load_vector_index(self) -> bool:
        try:
            vi = VectorIndex(self.vector_index_path)
            if vi.load():
                self.vindex = vi
                return True
        except Exception:
            self.vindex = None
        return False

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
            # Предполагаемая категория из БЗ (для согласования классификации)
            if relevant_articles:
                recommendations["kb_category"] = relevant_articles[0].get("category")
            
            # 2. Генерация рекомендуемых ответов (сначала по статьям из БЗ, иначе — категории)
            suggested_responses = await self._generate_suggested_from_articles(relevant_articles, analysis_result)
            if not suggested_responses:
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
            # 0) Лексический быстрый поиск (как раньше)
            text_results = await self.knowledge_base.search(text, limit=10)
            # Убедимся, что поля main_category/subcategory присутствуют
            for r in text_results:
                if not r.get("subcategory") and r.get("tags"):
                    r["subcategory"] = r["tags"][0] if len(r["tags"])>0 else None
                if not r.get("main_category"):
                    r["main_category"] = r.get("category")
            
            # Поиск по ключевым словам
            keyword_results = []
            for keyword in analysis_result.keywords[:3]:
                keyword_results.extend(await self.knowledge_base.search(keyword, limit=2))
            
            # Поиск по категории
            category_articles = await self.knowledge_base.get_category_articles(analysis_result.classification)

            # Эмбеддинг-поиск по персистентному индексу (если доступен)
            embed_index_results: List[Dict[str, Any]] = []
            try:
                if self.use_embeddings and self.vindex is not None:
                    qv = (await self.scibox_service.embed_texts([text]))[0]
                    for art_id, e_score in self.vindex.search(qv, top_k=5):
                        art = await self.knowledge_base.get_article_by_id(art_id)
                        if not art:
                            continue
                        embed_index_results.append({
                            "id": art.id,
                            "title": art.title,
                            "content": art.content,
                            "category": art.category.value,
                            "main_category": getattr(art, "main_category", None),
                            "subcategory": getattr(art, "subcategory", (art.tags[0] if art.tags else None)),
                            "tags": art.tags,
                            "relevance_score": 0.6,  # базовый вес
                            "embed_score": float(e_score),
                        })
            except Exception:
                pass
            category_results = [
                {
                    "id": article.id,
                    "title": article.title,
                    "content": article.content,
                    "category": article.category.value,
                    "main_category": getattr(article, "main_category", None),
                    "subcategory": getattr(article, "subcategory", (article.tags[0] if article.tags else None)),
                    "tags": article.tags,
                    "relevance_score": 0.8
                }
                for article in category_articles[:2]
            ]
            
            # Объединяем и убираем дубликаты
            all_results = text_results + keyword_results + category_results + embed_index_results
            # При необходимости усиливаем эмбеддингами
            if self.use_embeddings:
                all_results = await self._rerank_with_embeddings(text, all_results)
            # Убираем дубли по id, сохраняя лучший скор
            best_by_id: Dict[str, Dict[str, Any]] = {}
            for r in all_results:
                rid = r["id"]
                cur = best_by_id.get(rid)
                if (not cur) or (r.get("combined_score", r.get("relevance_score", 0)) > cur.get("combined_score", cur.get("relevance_score", 0))):
                    best_by_id[rid] = r
            unique_results = list(best_by_id.values())
            # Финальная сортировка по комбинированному скору, затем релевантности
            unique_results.sort(key=lambda x: x.get("combined_score", x.get("relevance_score", 0)), reverse=True)
            return unique_results[:5]
            
        except Exception as e:
            logger.error(f"Ошибка поиска релевантных статей: {str(e)}")
            return []

    async def _rerank_with_embeddings(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Реранжирование кандидатов с помощью эмбеддингов Scibox.
        Комбинируем cosine_similarity (alpha=0.7) с лексическим score.
        Кэшируем эмбеддинги статей по их id.
        """
        try:
            if not results:
                return results
            # 1) Эмбеддинг запроса
            q_emb = (await self.scibox_service.embed_texts([query]))[0]
            # 2) Эмбеддинги статей (title + content для лучшего сигнала)
            texts = []
            ids = []
            to_compute = []
            for r in results:
                rid = r["id"]
                ids.append(rid)
                if rid in self.embed_cache:
                    texts.append(None)  # плейсхолдер
                else:
                    txt = (r.get("title") or "") + "\n" + (r.get("content") or "")
                    to_compute.append((rid, txt))
            if to_compute:
                emb_new = await self.scibox_service.embed_texts([t for _, t in to_compute])
                for (rid, _), vec in zip(to_compute, emb_new):
                    self.embed_cache[rid] = vec
            # 3) Подсчет cosine и комбинированного скоринга
            def cos(a: List[float], b: List[float]) -> float:
                import math
                if not a or not b or len(a) != len(b):
                    return 0.0
                s = sum(x*y for x, y in zip(a, b))
                na = math.sqrt(sum(x*x for x in a)) or 1.0
                nb = math.sqrt(sum(y*y for y in b)) or 1.0
                return max(0.0, min(1.0, s/(na*nb)))
            alpha = 0.7
            reranked = []
            for r in results:
                rid = r["id"]
                e_score = cos(q_emb, self.embed_cache.get(rid, []))
                l_score = float(r.get("relevance_score", 0))
                combined = alpha * e_score + (1 - alpha) * l_score
                r2 = dict(r)
                r2["embed_score"] = round(e_score, 5)
                r2["combined_score"] = round(combined, 5)
                reranked.append(r2)
            reranked.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
            return reranked
        except Exception as e:
            logger.warning(f"_rerank_with_embeddings fallback: {e}")
            return results

    async def _generate_suggested_from_articles(self, articles: List[Dict[str, Any]], analysis_result: AnalysisResult) -> List[str]:
        """Формирование готовых ответов на основе контента статей из БЗ."""
        if not articles:
            return []
        suggestions: List[str] = []
        try:
            for art in articles[:3]:
                content = (art.get("content") or "").strip()
                if not content:
                    continue
                # Берем первую содержательную строку / предложение
                snippet = None
                for line in content.splitlines():
                    t = line.strip(" •-\t").strip()
                    if len(t) > 20:
                        snippet = t
                        break
                if not snippet:
                    snippet = content[:180] + ("..." if len(content) > 180 else "")
                suggestions.append(snippet)
            # Адаптация для негативной тональности
            if analysis_result.sentiment and analysis_result.sentiment < -0.3:
                suggestions = [
                    ("Приносим извинения за неудобства. " + s) if not s.lower().startswith("приносим извинения") else s
                    for s in suggestions
                ]
        except Exception:
            return []
        return suggestions[:3]

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