import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ..models import KnowledgeBaseArticle, RequestCategory, AnalysisResult

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    """
    Сервис базы знаний для поиска решений и генерации рекомендаций
    Использует синтетические данные для демонстрации функционала
    """
    
    def __init__(self):
        self.articles: List[KnowledgeBaseArticle] = []
        self.initialized = False
        
        # Синтетические данные для демонстрации
        self.synthetic_articles = [
            {
                "id": "tech_001",
                "title": "Ошибка подключения к серверу",
                "content": "Для решения проблем с подключением к серверу:\n1. Проверьте интернет-соединение\n2. Перезапустите приложение\n3. Обратитесь к системному администратору\n4. Проверьте настройки брандмауэра",
                "category": RequestCategory.TECHNICAL,
                "tags": ["подключение", "сервер", "ошибка", "интернет"],
                "solutions": [
                    "Перезагрузите роутер",
                    "Проверьте кабели",
                    "Свяжитесь с провайдером"
                ]
            },
            {
                "id": "bill_001", 
                "title": "Вопросы по оплате и списаниям",
                "content": "Помощь по вопросам оплаты:\n1. Проверьте статус платежа в личном кабинете\n2. Убедитесь, что карта не заблокирована\n3. Обратитесь в службу поддержки банка\n4. Используйте альтернативный способ оплаты",
                "category": RequestCategory.BILLING,
                "tags": ["оплата", "списание", "карта", "банк"],
                "solutions": [
                    "Проверьте баланс карты",
                    "Попробуйте другую карту",
                    "Обратитесь в банк"
                ]
            },
            {
                "id": "acc_001",
                "title": "Проблемы с доступом к аккаунту",
                "content": "Восстановление доступа к аккаунту:\n1. Используйте функцию 'Забыли пароль?'\n2. Проверьте email на наличие письма с восстановлением\n3. Обратитесь в службу поддержки\n4. Предоставьте документы для верификации",
                "category": RequestCategory.ACCOUNT,
                "tags": ["аккаунт", "пароль", "доступ", "восстановление"],
                "solutions": [
                    "Сбросьте пароль через email",
                    "Проверьте правильность логина",
                    "Обратитесь к администратору"
                ]
            },
            {
                "id": "gen_001",
                "title": "Общие вопросы использования",
                "content": "Ответы на часто задаваемые вопросы:\n1. Как пользоваться основными функциями\n2. Где найти справочную информацию\n3. Как связаться с поддержкой\n4. Где посмотреть обучающие материалы",
                "category": RequestCategory.GENERAL,
                "tags": ["справка", "инструкции", "обучение"],
                "solutions": [
                    "Изучите справочные материалы",
                    "Посмотрите видеоуроки",
                    "Обратитесь в службу поддержки"
                ]
            },
            {
                "id": "comp_001",
                "title": "Рассмотрение жалоб",
                "content": "Процедура рассмотрения жалоб:\n1. Зафиксируйте жалобу в системе\n2. Уведомите клиента о регистрации\n3. Проведите расследование\n4. Предоставьте ответ в установленные сроки",
                "category": RequestCategory.COMPLAINT,
                "tags": ["жалоба", "претензия", "расследование"],
                "solutions": [
                    "Зарегистрируйте жалобу",
                    "Назначьте ответственного",
                    "Проведите анализ",
                    "Предоставьте компенсацию при необходимости"
                ]
            },
            {
                "id": "feat_001",
                "title": "Запросы новых функций",
                "content": "Обработка запросов на новые функции:\n1. Зафиксируйте запрос в системе\n2. Оцените техническую возможность\n3. Передайте в отдел разработки\n4. Уведомите клиента о статусе",
                "category": RequestCategory.FEATURE_REQUEST,
                "tags": ["функция", "разработка", "улучшение"],
                "solutions": [
                    "Зарегистрируйте запрос",
                    "Оцените приоритет",
                    "Передайте разработчикам"
                ]
            }
        ]

    async def initialize(self):
        """Инициализация базы знаний"""
        try:
            # Загружаем синтетические данные
            self.articles = []
            for article_data in self.synthetic_articles:
                article = KnowledgeBaseArticle(
                    id=article_data["id"],
                    title=article_data["title"],
                    content=article_data["content"],
                    category=article_data["category"],
                    tags=article_data["tags"]
                )
                self.articles.append(article)
            
            self.initialized = True
            logger.info(f"База знаний инициализирована: {len(self.articles)} статей")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации базы знаний: {str(e)}")
            self.initialized = True  # Продолжаем работать

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Поиск в базе знаний по запросу
        """
        try:
            query_lower = query.lower()
            results = []
            
            for article in self.articles:
                relevance_score = self._calculate_relevance(article, query_lower)
                
                if relevance_score > 0:
                    # Получаем дополнительные данные из синтетической базы
                    article_data = next(
                        (item for item in self.synthetic_articles if item["id"] == article.id), 
                        {}
                    )
                    
                    result = {
                        "id": article.id,
                        "title": article.title,
                        "content": article.content,
                        "category": article.category.value,
                        "tags": article.tags,
                        "relevance_score": relevance_score,
                        "solutions": article_data.get("solutions", [])
                    }
                    results.append(result)
            
            # Сортируем по релевантности
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка поиска в базе знаний: {str(e)}")
            return []

    def _calculate_relevance(self, article: KnowledgeBaseArticle, query: str) -> float:
        """
        Вычисление релевантности статьи запросу
        """
        score = 0.0
        
        # Поиск в заголовке (высокий вес)
        if query in article.title.lower():
            score += 1.0
        
        # Поиск в тегах (средний вес)
        for tag in article.tags:
            if query in tag.lower() or tag.lower() in query:
                score += 0.7
        
        # Поиск в содержании (низкий вес)
        if query in article.content.lower():
            score += 0.3
        
        # Поиск отдельных слов
        query_words = query.split()
        for word in query_words:
            if len(word) > 3:  # Игнорируем короткие слова
                if word in article.title.lower():
                    score += 0.5
                elif word in article.content.lower():
                    score += 0.2
        
        return min(score, 1.0)  # Ограничиваем максимальный score

    async def get_category_articles(self, category: RequestCategory) -> List[KnowledgeBaseArticle]:
        """
        Получение статей по категории
        """
        return [article for article in self.articles if article.category == category]

    async def get_article_by_id(self, article_id: str) -> Optional[KnowledgeBaseArticle]:
        """
        Получение статьи по ID
        """
        return next((article for article in self.articles if article.id == article_id), None)

    async def add_article(self, title: str, content: str, category: RequestCategory, tags: List[str]) -> str:
        """
        Добавление новой статьи (для расширения базы знаний)
        """
        article_id = f"{category.value}_{str(uuid.uuid4())[:8]}"
        
        article = KnowledgeBaseArticle(
            id=article_id,
            title=title,
            content=content,
            category=category,
            tags=tags
        )
        
        self.articles.append(article)
        logger.info(f"Добавлена новая статья: {article_id}")
        
        return article_id

    async def get_recommended_responses(self, category: RequestCategory) -> List[str]:
        """
        Получение рекомендуемых ответов по категории
        """
        responses = {
            RequestCategory.TECHNICAL: [
                "Спасибо за обращение. Мы проверим техническую проблему и свяжемся с вами в течение часа.",
                "Попробуйте выполнить следующие действия и сообщите о результате.",
                "Передаю ваш запрос техническим специалистам для детального анализа."
            ],
            RequestCategory.BILLING: [
                "Проверим информацию по вашему счету и предоставим детальный отчет.",
                "Спасибо за информацию о проблеме с оплатой. Разберемся в течение рабочего дня.",
                "Рекомендую обратиться к вашему банку для уточнения статуса транзакции."
            ],
            RequestCategory.ACCOUNT: [
                "Поможем восстановить доступ к аккаунту. Следуйте инструкциям из письма.",
                "Для безопасности аккаунта необходимо подтвердить вашу личность.",
                "Создан запрос на восстановление доступа. Ожидайте письмо на email."
            ],
            RequestCategory.COMPLAINT: [
                "Ваша жалоба зарегистрирована. Номер обращения будет направлен на email.",
                "Приносим извинения за возникшие неудобства. Разберемся в ситуации.",
                "Передаю ваше обращение руководству для принятия мер."
            ],
            RequestCategory.GENERAL: [
                "Спасибо за обращение. Чем еще могу помочь?",
                "Надеюсь, предоставленная информация была полезной.",
                "Если у вас есть дополнительные вопросы, обращайтесь."
            ]
        }
        
        return responses.get(category, [
            "Спасибо за обращение. Мы рассмотрим ваш вопрос.",
            "Передаю ваш запрос соответствующим специалистам."
        ])

    async def health_check(self) -> Dict[str, Any]:
        """Проверка состояния базы знаний"""
        return {
            "status": "healthy" if self.initialized else "not_initialized",
            "articles_count": len(self.articles),
            "categories": list(set(article.category.value for article in self.articles))
        }