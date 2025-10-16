import asyncio
import httpx
import json
import re
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..models import AnalysisResult, Entity, EntityType, RequestCategory

logger = logging.getLogger(__name__)

class SciboxService:
    """
    Сервис интеграции с системой глубокого обучения Scibox
    Реализует извлечение именованных сущностей и классификацию текстов
    Также поддерживает генерацию ответов через Chat Completions.
    """
    
    def __init__(self, scibox_url: str = "http://localhost:8001", api_key: Optional[str] = None):
        self.scibox_url = scibox_url
        # Инициализируем, но далее всегда подхватываем актуальное значение из окружения
        self.api_key = api_key or os.getenv("SCIBOX_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.client = None
        self.initialized = False

        # Параметры Chat API (реальный Scibox OpenAI-совместимый)
        self.chat_base_url = os.getenv("SCIBOX_BASE_URL", "https://llm.t1v.scibox.tech/v1")
        self.chat_model = os.getenv("SCIBOX_CHAT_MODEL", os.getenv("MODEL_CHAT", "Qwen2.5-72B-Instruct-AWQ"))
        
        # Параметры Embeddings API (OpenAI-совместимый)
        self.embed_base_url = os.getenv("SCIBOX_EMBED_BASE_URL", self.chat_base_url)
        self.embed_model = os.getenv("SCIBOX_EMBED_MODEL", os.getenv("MODEL_EMBED", "text-embedding-3-large"))

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

    def _auth_headers(self) -> Dict[str, str]:
        """Формирует заголовки авторизации, динамически считывая токен из окружения,
        чтобы не зависеть от момента инициализации сервиса.
        """
        headers: Dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
        token = (os.getenv("SCIBOX_API_KEY") or os.getenv("OPENAI_API_KEY") or self.api_key or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            import logging as _logging
            _logging.getLogger(__name__).warning("SCIBOX API key is empty: Authorization header will be missing")
        return headers

    async def initialize(self):
        """Инициализация сервиса"""
        try:
            self.client = httpx.AsyncClient(timeout=30.0)
            
            # Проверяем доступность основного Scibox API через простой запрос
            try:
                headers = self._auth_headers()
                # Проверяем основной API endpoint вместо старого health
                test_payload = {"model": self.embed_model, "input": ["test"]}
                response = await self.client.post(
                    f"{self.embed_base_url}/embeddings",
                    headers=headers,
                    json=test_payload,
                    timeout=10.0
                )
                if response.status_code == 200:
                    logger.info(f"Подключение к Scibox API установлено ({self.embed_base_url})")
                elif response.status_code == 401:
                    logger.warning("Scibox API: неверный ключ авторизации, используем синтетические данные")
                else:
                    logger.warning(f"Scibox API вернул {response.status_code}, используем синтетические данные")
            except Exception as e:
                logger.info(f"Работаем с синтетическими данными (Scibox API недоступен: {e})")
            
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
            # TEMPORARY FIX: Skip Chat API due to timeout issues, use synthetic analysis
            # TODO: Fix Chat API timeout
            # if self.client:
            #     try:
            #         response = await self._call_scibox_api(text)
            #         if response:
            #             return response
            #     except Exception as e:
            #         logger.warning(f"Ошибка вызова Scibox API: {str(e)}")
            
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

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Получение эмбеддингов у Scibox (OpenAI-совместимый /v1/embeddings).
        Фолбэк: простая bag-of-words с хешированием.
        """
        if not texts:
            return []
        # Попытка реального Embeddings API
        try:
            headers = self._auth_headers()
            payload = {"model": self.embed_model, "input": texts}
            async with httpx.AsyncClient(timeout=60.0) as ac:
                resp = await ac.post(f"{self.embed_base_url}/embeddings", headers=headers, json=payload)
                if resp.status_code == 401:
                    logger.error("Embeddings API 401: no/invalid API key sent. Ensure SCIBOX_API_KEY is loaded.")
                if resp.status_code == 200:
                    data = resp.json()
                    vectors = [item.get("embedding", []) for item in data.get("data", [])]
                    if vectors and all(isinstance(v, list) and v for v in vectors):
                        return vectors
                else:
                    logger.warning(f"Embed API non-200: {resp.status_code}; body_head={resp.text[:300]}")
        except Exception as e:
            logger.warning(f"Embeddings API недоступен, используем фолбэк: {e}")
        # Фолбэк: простая хеш-векторизация с фиксированной размерностью
        return [self._hash_embedding(t) for t in texts]

    def _hash_embedding(self, text: str, dim: int = 384) -> List[float]:
        import hashlib
        import math
        vec = [0.0] * dim
        tokens = [w for w in re.findall(r"\b\w+\b", text.lower()) if w]
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % dim
            vec[idx] += 1.0
        # L2-норма
        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def _call_scibox_api(self, text: str) -> Optional[AnalysisResult]:
        """
        Реализация анализа через OpenAI-совместимый Chat Completions SciBox.
        Модель возвращает строго JSON со структурой анализа.
        """
        try:
            headers = self._auth_headers()
            system_prompt = (
                "Ты NER+Classifier для службы поддержки. Верни ТОЛЬКО компактный JSON без пояснений. "
                "Схема: {\n"
                "  \"classification\": one_of[technical,billing,account,complaint,feature_request,general],\n"
                "  \"entities\": [{text, type(one_of[phone,email,account_number,amount,date,error_code,person,product,address]), confidence(0..1), start, end}],\n"
                "  \"sentiment\": {\"score\": float -1..1},\n"
                "  \"keywords\": [string...],\n"
                "  \"language\": \"ru\"|\"en\"\n"
                "}\n"
                "Если нет позиций, укажи start/end=-1."
            )
            user_prompt = f"Текст обращения:\n{text}"
            payload = {
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 400,
            }
            async with httpx.AsyncClient(timeout=60.0) as ac:
                resp = await ac.post(f"{self.chat_base_url}/chat/completions", headers=headers, json=payload)
            if resp.status_code == 401:
                logger.error("Chat API 401: no/invalid API key sent. Ensure SCIBOX_API_KEY is loaded.")
            if resp.status_code != 200:
                logger.error(f"Chat API error {resp.status_code}: {resp.text[:400]}")
                return None
            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            parsed = self._extract_json_safe(content)
            if not parsed:
                return None
            return self._parse_scibox_response(parsed, text)
        except Exception as e:
            logger.error(f"Ошибка вызова Scibox Chat API: {str(e)}", exc_info=True)
            return None

    def _parse_scibox_response(self, data: Dict, original_text: str) -> AnalysisResult:
        """
        Парсинг ответа Chat Completions SciBox в наш формат
        """
        entities = []
        for entity_data in data.get("entities", []) or []:
            etype_raw = str(entity_data.get("type", "person")).lower()
            try:
                etype = EntityType(etype_raw)
            except Exception:
                etype = EntityType.PERSON
            try:
                start_pos = int(entity_data.get("start", -1))
                end_pos = int(entity_data.get("end", -1))
            except Exception:
                start_pos, end_pos = -1, -1
            conf = float(entity_data.get("confidence", 0.7) or 0.7)
            entities.append(Entity(
                text=str(entity_data.get("text", "")),
                type=etype,
                confidence=max(0.0, min(1.0, conf)),
                start_pos=start_pos if start_pos >= 0 else 0,
                end_pos=end_pos if end_pos >= 0 else 0,
            ))
        # Категория
        cat_raw = None
        classification = data.get("classification")
        if isinstance(classification, dict):
            cat_raw = classification.get("category")
            conf_val = float(classification.get("confidence", 0.7))
        else:
            cat_raw = classification
            conf_val = 0.7
        try:
            cat_enum = RequestCategory(str(cat_raw or "general").lower())
        except Exception:
            cat_enum = RequestCategory.GENERAL
        # Остальные поля
        sentiment = None
        if isinstance(data.get("sentiment"), dict):
            try:
                sentiment = float(data["sentiment"].get("score", 0.0))
            except Exception:
                sentiment = 0.0
        keywords = data.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []
        return AnalysisResult(
            classification=cat_enum,
            entities=entities,
            confidence=max(0.0, min(1.0, conf_val)),
            sentiment=sentiment,
            keywords=[str(k) for k in keywords][:10],
            language=str(data.get("language", "ru"))
        )

    def _extract_json_safe(self, content: str) -> Optional[Dict[str, Any]]:
        """Выделяет JSON из контента LLM (обрезает кодовые блоки, берёт { .. })."""
        try:
            s = content.strip()
            # Убираем возможные ```json ... ```
            if s.startswith("```"):
                s = s.strip("`\n ")
                # после среза может остаться 'json' префикс
                if s.lower().startswith("json"):
                    s = s[4:].lstrip("\n ")
            # Ищем первый '{' и последний '}'
            i = s.find('{')
            j = s.rfind('}')
            if i != -1 and j != -1 and j > i:
                import json as _json
                return _json.loads(s[i:j+1])
        except Exception:
            return None
        return None

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
            # 1) Попытка стандартного /health (если доступен)
            if self.client:
                try:
                    response = await self.client.get(f"{self.scibox_url}/health")
                    if response.status_code == 200:
                        return {"status": "connected", "message": "Подключен к Scibox (/health)"}
                except Exception:
                    pass
            # 2) Попытка OpenAI-совместимого /v1/models
            try:
                headers = self._auth_headers()
                async with httpx.AsyncClient(timeout=15.0) as ac:
                    r = await ac.get(f"{self.chat_base_url}/models", headers=headers or None)
                if r.status_code == 200 and r.json().get("object") == "list":
                    return {"status": "connected", "message": "Подключен к Scibox (/v1/models)", "auth": True}
                elif r.status_code in (401, 403):
                    return {"status": "auth_error", "message": "Неверный или отсутствует API ключ", "auth": False}
            except Exception as e:
                return {"status": "error", "message": f"Ошибка: {str(e)}"}
            # 3) Фолбэк
            return {"status": "synthetic", "message": "Работает с синтетическими данными"}
        except Exception as e:
            return {"status": "error", "message": f"Ошибка: {str(e)}"}

    async def close(self):
        """Закрытие соединений"""
        if self.client:
            await self.client.aclose()

    async def generate_answer_from_kb(self, question: str, articles: List[Dict[str, Any]], temperature: float = 0.2, max_tokens: int = 400) -> str:
        """
        Генерация ответа по БЗ через Chat Completions. При недоступности API — фолбэк из контента статей.
        """
        # Подготовка контекста
        context_parts = []
        for a in articles[:5]:
            title = a.get("title") or a.get("id")
            content = a.get("content", "")
            context_parts.append(f"Заголовок: {title}\nОтвет: {content}")
        context = "\n\n".join(context_parts) if context_parts else ""
        system_prompt = (
            "Ты помощник службы поддержки банка. Отвечай КРАТКО (1–2 предложения) и понятным языком, только на русском. "
            "Опирайся ТОЛЬКО на Базу Знаний ниже, НЕ цитируй длинные фрагменты дословно, не добавляй фактов вне БЗ. "
            "Если информации недостаточно, скажи об этом и что нужен уточняющий вопрос."
        )
        user_prompt = (
            f"Вопрос клиента: {question}\n\n"
            f"База знаний (фрагменты):\n{context}\n\n"
            "Сделай выжимку ответа (1–2 коротких предложения) для оператора."
        )

        # Пытаемся вызвать реальный Chat API Scibox
        try:
            headers = self._auth_headers()
            payload = {
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            async with httpx.AsyncClient(timeout=60.0) as ac:
                resp = await ac.post(f"{self.chat_base_url}/chat/completions", headers=headers, json=payload)
                logger.info(f"Scibox Chat API call: url={self.chat_base_url}/chat/completions model={self.chat_model} status={resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    if content:
                        return content
                else:
                    body = resp.text
                    logger.warning(f"Scibox Chat API non-200: {resp.status_code}; body_head={body[:400]}")
        except Exception as e:
            logger.warning(f"Chat API недоступен, используем фолбэк: {e}")

        # Фолбэк: собрать краткий ответ из первых строк БЗ
        for a in articles:
            c = (a.get("content") or "").strip()
            if c:
                lines = [ln.strip(" •-\t").strip() for ln in c.splitlines() if ln.strip()]
                for ln in lines:
                    if len(ln) > 30:
                        return ln
        return "К сожалению, информации в базе знаний недостаточно. Уточните детали у клиента."
