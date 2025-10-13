# Smart Support: ИИ-ассистент службы поддержки

![Smart Support Logo](https://img.shields.io/badge/Smart_Support-ИИ_ассистент-blue?style=for-the-badge&logo=robot)

Интеллектуальная система поддержки клиентов с интеграцией **Scibox** для анализа запросов в режиме реального времени.

## 🎯 Описание проекта

Smart Support — это современная система анализа обращений в службу поддержки, которая использует возможности искусственного интеллекта для:

- **Автоматической классификации** обращений по категориям
- **Извлечения ключевых сущностей** (телефоны, email, номера счетов, суммы)
- **Анализа тональности** обращения клиента
- **Генерации рекомендаций** для операторов на основе базы знаний
- **Real-time подсказок** во время работы с обращениями

### 🔧 Технологический стек

**Backend:**
- Python 3.11+
- FastAPI (веб-фреймворк)
- WebSocket (real-time коммуникация)
- Pydantic (валидация данных)

**Frontend:**
- HTML5/CSS3/JavaScript (ES6+)
- Bootstrap 5 (UI компоненты)
- WebSocket API (real-time)

**Интеграции:**
- **Scibox** (система глубокого обучения)
- Redis (кэширование)
- PostgreSQL (база данных)

**DevOps:**
- Docker & Docker Compose
- Nginx (reverse proxy)
- Prometheus & Grafana (мониторинг)

## 🚀 Быстрый старт

### Предварительные требования

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+
- Git

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-username/smart-support.git
cd smart-support
```

### 2. Запуск через Docker Compose

```bash
# Базовая конфигурация (только основные сервисы)
docker-compose up -d smart-support redis postgres scibox-mock

# Полная конфигурация с мониторингом
docker-compose up -d
```

### 3. Проверка статуса

```bash
# Проверка состояния контейнеров
docker-compose ps

# Проверка логов
docker-compose logs -f smart-support
```

### 4. Доступ к приложению

- **Web-интерфейс**: http://localhost:8000
- **API документация**: http://localhost:8000/docs
- **Scibox Mock API**: http://localhost:8001/docs
- **Grafana (мониторинг)**: http://localhost:3000 (admin/admin123)

## 📋 Инструкция по использованию

### Для операторов поддержки

1. **Откройте** веб-интерфейс по адресу http://localhost:8000
2. **Введите** информацию о клиенте (опционально)
3. **Вставьте** текст обращения в поле "Текст обращения"
4. **Выберите** канал обращения (веб, телефон, email, чат)
5. **Нажмите** "Анализировать запрос"

### Результат анализа

Система автоматически:
- **Определит категорию** обращения (техническая проблема, биллинг, аккаунт, жалоба)
- **Извлечет сущности** (номера телефонов, email, коды ошибок, суммы)
- **Оценит тональность** (позитивная, негативная, нейтральная)
- **Предложит готовые ответы** на основе базы знаний
- **Даст рекомендации** по дальнейшим действиям

### Примеры запросов для тестирования

```
У меня не получается войти в личный кабинет. Пишет ошибка 404. 
Мой номер телефона +7 (900) 123-45-67
```

```
Здравствуйте! С моего счета 4276 1234 5678 9012 списали 5000 рублей, 
но я не делал покупок. Что делать?
```

```
Очень недоволен качеством обслуживания! Вчера обратился в офис, 
никто не помог. Требую разбирательства!
```

## 🏗️ Архитектура системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │◄──►│  Smart Support  │◄──►│   Scibox API    │
│   (Frontend)    │    │    (Backend)    │    │ (ML Analysis)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Knowledge Base  │
                    │   (Synthetic)   │
                    └─────────────────┘
```

### Основные компоненты

1. **Web Frontend** - Интерфейс оператора
2. **FastAPI Backend** - API сервер
3. **Scibox Service** - Интеграция с ML системой
4. **Knowledge Base** - База знаний с решениями
5. **WebSocket Manager** - Real-time коммуникация
6. **Recommendation Engine** - Генерация рекомендаций

## 🔌 API Endpoints

### Основные эндпоинты

```http
POST /api/analyze
Content-Type: application/json

{
  "request_id": "req_123456",
  "text": "Текст обращения клиента",
  "customer_id": "client_001",
  "channel": "web"
}
```

```http
POST /api/feedback
Content-Type: application/json

{
  "request_id": "req_123456",
  "recommendation_quality": 4,
  "response_used": true,
  "operator_comments": "Рекомендации были полезными"
}
```

```http
GET /health
```

### WebSocket подключение

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/client_id');

// Отправка запроса на анализ
ws.send(JSON.stringify({
  type: 'analyze_request',
  data: {
    request_id: 'req_123',
    text: 'Текст обращения'
  }
}));
```

## 🛠️ Разработка

### Локальная разработка

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск в режиме разработки
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Структура проекта

```
smart-support/
├── app/                          # Backend приложение
│   ├── main.py                   # Основной файл FastAPI
│   ├── models.py                 # Pydantic модели
│   ├── database.py               # Настройки БД
│   ├── websocket_manager.py      # WebSocket менеджер
│   └── services/                 # Бизнес-логика
│       ├── scibox_service.py     # Интеграция с Scibox
│       ├── knowledge_base.py     # База знаний
│       └── recommendation_engine.py
├── static/                       # Frontend файлы
│   ├── index.html               # Главная страница
│   ├── app.js                   # JavaScript приложение
│   └── style.css                # Стили
├── scibox-mock/                 # Mock Scibox API
│   └── mock_scibox.py
├── docker-compose.yml           # Docker Compose конфигурация
├── Dockerfile                   # Docker образ
├── requirements.txt             # Python зависимости
└── README.md                    # Документация
```

### Добавление новых функций

1. **Новая категория обращений**: Обновите `RequestCategory` в `models.py`
2. **Новый тип сущности**: Добавьте в `EntityType` и обновите паттерны
3. **Расширение базы знаний**: Добавьте статьи в `KnowledgeBaseService`

## 🐳 Docker развертывание

### Быстрое развертывание

```bash
# Только основные сервисы
docker-compose up -d smart-support redis postgres scibox-mock
```

### Полное развертывание с мониторингом

```bash
# Все сервисы включая Grafana и Prometheus
docker-compose up -d
```

### Масштабирование

```bash
# Запуск нескольких экземпляров приложения
docker-compose up -d --scale smart-support=3
```

### Мониторинг логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f smart-support
```

## 📊 Мониторинг и метрики

### Grafana Dashboard

- **URL**: http://localhost:3000
- **Логин**: admin
- **Пароль**: admin123

### Основные метрики

- Количество обращений в минуту
- Время обработки запросов
- Точность классификации
- Использование рекомендаций
- Статус сервисов

### Prometheus метрики

- **URL**: http://localhost:9090
- Доступные метрики системы и бизнес-метрики

## 🔧 Конфигурация

### Переменные окружения

```env
# Основные настройки
ENVIRONMENT=production
LOG_LEVEL=INFO

# Интеграции
SCIBOX_URL=http://scibox:8001
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://user:pass@postgres:5432/db

# Безопасность
SECRET_KEY=your-secret-key
```

### Настройка Scibox интеграции

В `docker-compose.yml` укажите реальный URL Scibox:

```yaml
environment:
  - SCIBOX_URL=http://your-scibox-server:port
```

## 🚨 Troubleshooting

### Проблемы с запуском

```bash
# Очистка Docker кэша
docker system prune -a

# Пересборка образов
docker-compose build --no-cache
```

### Проблемы с подключением к Scibox

1. Проверьте доступность Scibox API
2. Убедитесь в правильности URL в переменных окружения
3. Проверьте логи: `docker-compose logs scibox-mock`

### WebSocket подключения

- Проверьте firewall настройки
- Убедитесь что порт 8000 доступен
- Проверьте proxy настройки

## 📈 Roadmap

### В планах

- [ ] Интеграция с реальным Scibox
- [ ] Поддержка множественных языков
- [ ] Продвинутая аналитика
- [ ] Интеграция с CRM системами
- [ ] Mobile приложение
- [ ] A/B тестирование рекомендаций

## 👥 Команда разработки

- **ML/Backend Developer** - Интеграция с Scibox, API разработка
- **Frontend Developer** - Пользовательский интерфейс
- **DevOps Engineer** - Контейнеризация и развертывание

## 📄 Лицензия

Проект разработан для хакатона "Smart Support: поддержка нового поколения"

## 🤝 Contributing

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

---

**Smart Support** - Революция в службе поддержки с помощью ИИ! 🚀