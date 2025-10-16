"""
Сервис категоризации запросов на основе сравнения эмбеддингов с базой знаний
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class EmbeddingCategorizer:
    """Категоризатор на основе эмбеддингов БЗ"""
    
    def __init__(self, knowledge_base=None, scibox_service=None):
        self.knowledge_base = knowledge_base
        self.scibox_service = scibox_service
        self.kb_embeddings = {}
        self.articles_cache = []
    
    async def initialize_from_knowledge_base(self):
        """Инициализация категоризатора с эмбеддингами из БЗ"""
        if not self.knowledge_base or not self.scibox_service:
            logger.error("Knowledge base or Scibox service not provided")
            return False
            
        try:
            # Кешируем статьи из БЗ
            self.articles_cache = self.knowledge_base.articles
            
            if not self.articles_cache:
                logger.warning("No articles found in knowledge base")
                return False
            
            # Генерируем эмбеддинги для всех вопросов из БЗ
            titles = [article.title for article in self.articles_cache]
            
            logger.info(f"Generating embeddings for {len(titles)} KB articles...")
            embeddings = await self.scibox_service.embed_texts(titles)
            
            # Сохраняем эмбеддинги с соответствующими статьями
            self.kb_embeddings = {
                self.articles_cache[i].id: embeddings[i] 
                for i in range(len(self.articles_cache))
            }
            
            logger.info(f"Successfully initialized categorizer with {len(self.kb_embeddings)} embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize categorizer: {e}")
            return False

    async def categorize_text(self, text: str) -> Tuple[str, str, float]:
        """
        Категоризация текста через сравнение эмбеддингов с вопросами из БЗ
        
        Returns:
            Tuple[category, subcategory, confidence]
        """
        try:
            if not self.kb_embeddings or not self.scibox_service:
                logger.warning("Categorizer not initialized, returning default")
                return "general", "consultation", 0.3
            
            # Получаем эмбеддинг входящего вопроса
            query_embeddings = await self.scibox_service.embed_texts([text])
            query_embedding = query_embeddings[0]
            
            # Сравниваем с всеми эмбеддингами вопросов из БЗ
            best_similarity = 0.0
            best_article = None
            
            for article in self.articles_cache:
                if article.id in self.kb_embeddings:
                    kb_embedding = self.kb_embeddings[article.id]
                    
                    # Вычисляем cosine similarity
                    similarity = cosine_similarity(
                        [query_embedding], [kb_embedding]
                    )[0][0]
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_article = article
            
            if best_article and best_similarity > 0.3:  # Минимальный порог сходства
                category = best_article.main_category or best_article.category.value
                subcategory = best_article.subcategory or "общие"
                confidence = min(best_similarity, 0.95)  # Максимальная уверенность 95%
                
                logger.debug(f"Found best match: '{best_article.title}' (similarity: {best_similarity:.3f})")
                logger.debug(f"Category: {category}, Subcategory: {subcategory}")
                
                return category, subcategory, confidence
            else:
                logger.debug(f"No good match found, best similarity: {best_similarity:.3f}")
                return "общие вопросы", "консультация", 0.3
                
        except Exception as e:
            logger.error(f"Error in embedding categorization: {e}")
            return "общие вопросы", "консультация", 0.3

    def get_category_display_name(self, category: str) -> str:
        """Получить отображаемое имя категории"""
        return category  # Возвращаем категорию как есть из БЗ

    def get_subcategory_display_name(self, category: str, subcategory: str) -> str:
        """Получить отображаемое имя подкатегории"""
        return subcategory  # Возвращаем подкатегорию как есть из БЗ

    async def get_text_embedding(self, text: str) -> np.ndarray:
        """Получение эмбеддинга текста (заглушка, в реальности использовать модель)"""
        # Временная заглушка - создаем простой эмбеддинг на основе ключевых слов
        embedding = np.zeros(100)  # Размерность эмбеддинга
        
        text_lower = text.lower()
        
        # Простая эвристика на основе ключевых слов
        for i, (category, keywords) in enumerate(self.category_keywords.items()):
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                embedding[i] = score / len(keywords)
        
        # Добавляем немного случайности для разнообразия
        embedding += np.random.normal(0, 0.1, len(embedding))
        
        return embedding / (np.linalg.norm(embedding) + 1e-8)  # Нормализация

    async def categorize_text(self, text: str) -> Tuple[str, str, float]:
        """
        Категоризация текста через эмбеддинги
        
        Returns:
            Tuple[category, subcategory, confidence]
        """
        try:
            # Получаем эмбеддинг текста
            text_embedding = await self.get_text_embedding(text)
            
            # Находим лучшую категорию через эвристики
            best_category = await self._find_best_category(text)
            best_subcategory = await self._find_best_subcategory(text, best_category)
            
            # Вычисляем уверенность
            confidence = await self._calculate_confidence(text, best_category, best_subcategory)
            
            return best_category, best_subcategory, confidence
            
        except Exception as e:
            logger.error(f"Error in categorization: {e}")
            return "general", "consultation", 0.5

    async def _find_best_category(self, text: str) -> str:
        """Находим лучшую категорию"""
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in self.category_keywords.items():
            # Подсчитываем совпадения ключевых слов
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    # Бонус за точное совпадение слова (не подстроки)
                    import re
                    if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                        score += 2
                    else:
                        score += 1
            scores[category] = score
        
        # Логируем для отладки
        logger.debug(f"Categorization scores for '{text[:50]}...': {scores}")
        
        # Возвращаем категорию с максимальным счетом
        best_category = max(scores.items(), key=lambda x: x[1])
        return best_category[0] if best_category[1] > 0 else "general"

    async def _find_best_subcategory(self, text: str, category: str) -> str:
        """Находим лучшую подкатегорию для данной категории"""
        text_lower = text.lower()
        
        if category not in self.category_structure:
            return "other"
        
        subcategories = self.category_structure[category]["subcategories"]
        
        # Простые правила для определения подкатегории
        subcategory_rules = {
            "technical": {
                "login_issues": ["вход", "логин", "пароль", "авторизация", "войти"],
                "performance": ["медленно", "зависает", "тормозит", "производительность"],
                "bugs": ["ошибка", "баг", "не работает", "сломалось"],
                "integration": ["интеграция", "подключение", "api"],
                "api_errors": ["api", "запрос", "ответ", "endpoint"]
            },
            "billing": {
                "payment_issues": ["оплата", "платеж", "не прошел", "отклонен"],
                "invoice_questions": ["счет", "инвойс", "накладная"],
                "pricing": ["тариф", "цена", "стоимость", "план"],
                "refunds": ["возврат", "компенсация", "вернуть"],
                "subscription": ["подписка", "продление", "отмена"]
            },
            "general": {
                "how_to": ["как", "каким образом", "способ"],
                "features": ["функция", "возможность", "что умеет"],
                "documentation": ["документация", "инструкция", "руководство"],
                "best_practices": ["лучше", "правильно", "рекомендация"],
                "consultation": ["помогите", "консультация", "совет"]
            },
            "account": {
                "registration": ["регистрация", "создать", "аккаунт"],
                "profile_settings": ["профиль", "настройки", "изменить"],
                "security": ["безопасность", "пароль", "защита"],
                "data_management": ["данные", "экспорт", "импорт"],
                "permissions": ["доступ", "права", "разрешения"]
            },
            "complaint": {
                "service_quality": ["качество", "плохо", "ужасно"],
                "response_time": ["долго", "медленно", "время"],
                "functionality": ["не работает", "функция"],
                "support_team": ["поддержка", "оператор"],
                "other": ["жалоба", "недоволен"]
            },
            "feature_request": {
                "new_features": ["добавьте", "новая", "хочу"],
                "improvements": ["улучшите", "лучше", "исправьте"],
                "customization": ["настройка", "кастомизация"],
                "mobile_app": ["мобильное", "приложение", "телефон"],
                "reporting": ["отчет", "статистика", "аналитика"]
            }
        }
        
        if category in subcategory_rules:
            rules = subcategory_rules[category]
            scores = {}
            
            for subcategory, keywords in rules.items():
                score = sum(1 for keyword in keywords if keyword in text_lower)
                scores[subcategory] = score
            
            if scores:
                best_subcategory = max(scores.items(), key=lambda x: x[1])
                if best_subcategory[1] > 0:
                    return best_subcategory[0]
        
        # Возвращаем первую подкатегорию по умолчанию
        return list(subcategories.keys())[0]

    async def _calculate_confidence(self, text: str, category: str, subcategory: str) -> float:
        """Вычисляем уверенность в категоризации"""
        text_lower = text.lower()
        
        # Базовая уверенность на основе ключевых слов
        if category in self.category_keywords:
            keywords = self.category_keywords[category]
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            base_confidence = min(matches / len(keywords), 1.0)
        else:
            base_confidence = 0.3
        
        # Корректируем уверенность
        confidence = max(0.3, min(0.95, base_confidence + 0.2))
        
        return confidence

    def get_category_display_name(self, category: str) -> str:
        """Получить отображаемое имя категории"""
        if category in self.category_structure:
            return self.category_structure[category]["name"]
        return category.title()

    def get_subcategory_display_name(self, category: str, subcategory: str) -> str:
        """Получить отображаемое имя подкатегории"""
        if (category in self.category_structure and 
            subcategory in self.category_structure[category]["subcategories"]):
            return self.category_structure[category]["subcategories"][subcategory]
        return subcategory.replace("_", " ").title()