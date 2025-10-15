import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

import pandas as pd

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

        # Путь к Excel-базе знаний (если задан — используем её вместо синтетической)
        self.kb_excel_path = os.getenv("KNOWLEDGE_BASE_XLSX")
        self.kb_sheet = os.getenv("KB_SHEET")  # имя листа или индекс
        # Переопределение колонок (если структура отличается)
        self.kb_col_title = os.getenv("KB_COL_TITLE")
        self.kb_col_content = os.getenv("KB_COL_CONTENT")
        # Явные имена колонок для основной/подкатегории
        self.kb_col_main_category = os.getenv("KB_COL_MAIN_CATEGORY") or os.getenv("KB_COL_CATEGORY")
        self.kb_col_subcategory = os.getenv("KB_COL_SUBCATEGORY")
        self.kb_col_tags = os.getenv("KB_COL_TAGS")
        # JSON-мэппинг категорий Excel -> RequestCategory
        self.kb_category_map_raw = os.getenv("KB_CATEGORY_MAP")

        # Синтетические данные для демонстрации (используются, если Excel не задан)
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
            self.articles = []

            if self.kb_excel_path and os.path.exists(self.kb_excel_path):
                loaded = self._load_from_excel(self.kb_excel_path)
                if loaded:
                    self.initialized = True
                    logger.info(
                        f"База знаний загружена из Excel: {self.kb_excel_path}, статей: {len(self.articles)}"
                    )
                    return
                else:
                    logger.warning("Не удалось загрузить Excel, используем синтетическую базу знаний")

            # Fallback: синтетические данные
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
            logger.info(f"База знаний инициализирована (synthetic): {len(self.articles)} статей")

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
                        "main_category": article.main_category,
                        "subcategory": article.subcategory,
                        "tags": article.tags,
                        "relevance_score": relevance_score,
                        "solutions": article_data.get("solutions", [])
                    }
                    results.append(result)
            
            # Сортируем по релевантности
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            if not results:
                # Фолбэк: если ничего не найдено, вернуть первые N статей (для демонстрации)
                fallback = []
                for article in self.articles[:limit]:
                    fallback.append({
                        "id": article.id,
                        "title": article.title,
                        "content": article.content,
                        "category": article.category.value,
                        "tags": article.tags,
                        "relevance_score": 0.1,
                    })
                return fallback
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка поиска в базе знаний: {str(e)}")
            return []

    def _load_from_excel(self, path: str) -> bool:
        try:
            # Выбор листа
            sheet = 0
            if self.kb_sheet:
                try:
                    sheet = int(self.kb_sheet)
                except ValueError:
                    sheet = self.kb_sheet

            df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
            if df is None or df.empty:
                return False

            # Нормализуем имена колонок для автоопределения
            norm = {c: str(c).strip().lower() for c in df.columns}
            inv = {v: k for k, v in norm.items()}

            def pick(name: Optional[str], candidates: List[str]) -> Optional[str]:
                # Явно заданное имя столбца
                if name and name in df.columns:
                    return name
                # Точное совпадение по нормализованному имени
                for cand in candidates:
                    if cand in inv:
                        return inv[cand]
                # Частичное совпадение (подстрока)
                for c_idx, c in enumerate(df.columns):
                    nc = norm[c]
                    for cand in candidates:
                        if cand in nc or nc in cand:
                            return c
                return None

            # Расширенные синонимы для автоопределения колонок
            title_candidates = [
                "title","заголовок","вопрос","пример вопроса","query","question"
            ]
            content_candidates = [
                "content","ответ","шаблонный ответ","answer","text","body"
            ]
            category_candidates = [
                "категория","category","основная категория","main category"
            ]
            subcategory_candidates = [
                "подкатегория","subcategory","раздел"
            ]
            tags_candidates = [
                "tags","теги","keywords"
            ]

            col_title = pick(self.kb_col_title, title_candidates) or list(df.columns)[0]
            col_content = pick(self.kb_col_content, content_candidates) or list(df.columns)[1]
            col_main_category = pick(self.kb_col_main_category, category_candidates) or None
            col_subcategory = pick(self.kb_col_subcategory, subcategory_candidates) or None
            col_tags = pick(self.kb_col_tags, tags_candidates) or None

            cat_map: Dict[str, str] = {}
            if self.kb_category_map_raw:
                try:
                    cat_map = json.loads(self.kb_category_map_raw)
                except Exception:
                    cat_map = {}

            def map_category(val: Optional[str]) -> (RequestCategory, str):
                if not val:
                    return RequestCategory.GENERAL, ""
                raw = str(val).strip()
                mapped = cat_map.get(raw, raw).lower()
                try:
                    return RequestCategory(mapped), raw
                except Exception:
                    # эвристика
                    if "тех" in mapped or "tech" in mapped:
                        return RequestCategory.TECHNICAL, raw
                    if "оплат" in mapped or "bill" in mapped or "счет" in mapped:
                        return RequestCategory.BILLING, raw
                    if "аккаун" in mapped or "доступ" in mapped or "парол" in mapped:
                        return RequestCategory.ACCOUNT, raw
                    if "жалоб" in mapped or "претенз" in mapped:
                        return RequestCategory.COMPLAINT, raw
                    if "функц" in mapped or "feature" in mapped:
                        return RequestCategory.FEATURE_REQUEST, raw
                    return RequestCategory.GENERAL, raw

            for idx, row in df.iterrows():
                title = str(row.get(col_title, "")).strip()
                content = str(row.get(col_content, "")).strip()
                main_raw = str(row.get(col_main_category, "")).strip() if col_main_category else ""
                sub_raw = str(row.get(col_subcategory, "")).strip() if col_subcategory else ""
                cat_enum, cat_raw = map_category(main_raw or sub_raw)
                tags_val = row.get(col_tags, "") if col_tags else ""
                if isinstance(tags_val, str):
                    tags = [t.strip() for t in tags_val.split(",") if t and str(t).strip()]
                elif isinstance(tags_val, (list, tuple)):
                    tags = [str(t).strip() for t in tags_val if str(t).strip()]
                else:
                    tags = []
                # Добавляем исходное описание категории как тег для лучшего поиска
                if cat_raw:
                    tags.append(cat_raw)
                if sub_raw:
                    tags.append(sub_raw)

                art_id = f"kb_{cat_enum.value}_{idx}"
                self.articles.append(
                    KnowledgeBaseArticle(
                        id=art_id,
                        title=title or (content[:40] + "...") if content else art_id,
                        content=content or title,
                        category=cat_enum,
                        main_category=main_raw or cat_raw,
                        subcategory=sub_raw or None,
                        tags=tags,
                    )
                )

            return len(self.articles) > 0
        except Exception as e:
            logger.error(f"Ошибка загрузки Excel: {e}")
            return False

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