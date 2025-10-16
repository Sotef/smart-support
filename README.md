# Smart Support: ИИ-ассистент службы поддержки

![Smart Support Logo](https://img.shields.io/badge/Smart_Support-ИИ_ассистент-blue?style=for-the-badge&logo=robot)

Интеллектуальная система поддержки клиентов с **реальным чатом оператор-клиент**, интеграцией **Scibox** для анализа запросов и **ИИ-рекомендациями** в режиме реального времени.

## 🎯 Описание проекта

Smart Support — это современная система поддержки клиентов в режиме реального времени, которая использует возможности искусственного интеллекта для:

## 🚀 Основные возможности

### 💬 Реальный чат оператор-клиент
- **WebSocket соединение** для мгновенного обмена сообщениями
- **Галочки прочтения** (✓✓) для отслеживания статуса сообщений
- **Горячие клавиши** (Ctrl+Enter для отправки, Tab для переключения)
- **Контекстное меню** для работы с сообщениями (ответ, редактирование, удаление)
- **Автоскролл** к новым сообщениям

### 🧠 ИИ-анализ в реальном времени
- **Автоматическая классификация** каждого сообщения клиента по категориям
- **Извлечение ключевых сущностей** (телефоны, email, номера счетов, суммы)
- **Анализ тональности** сообщений (позитивная/негативная/нейтральная)
- **Генерация рекомендаций** для операторов на основе базы знаний
- **Сворачиваемые умные ответы** с показом количества

### 📊 Панель анализа для операторов
- **Детальная аналитика** каждого вопроса клиента
- **Категории и подкатегории** с процентом уверенности ИИ
- **Ключевые слова** из сообщений
- **Сворачиваемый интерфейс** для экономии места

### 🔧 Технологический стек

**Backend:**
- Python 3.11+
- FastAPI (веб-фреймворк)
- WebSocket (real-time коммуникация)
- Pydantic (валидация данных)

**Frontend:**
- **Next.js 15** (React framework)
- **React 19** с TypeScript
- **Tailwind CSS** + **Radix UI** (современные компоненты)
- **WebSocket API** (real-time коммуникация)
- **shadcn/ui** (компонентная библиотека)

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

**Локальное развертывание:**
- **Backend API**: http://localhost:8000
- **API документация**: http://localhost:8000/docs  
- **Frontend (vtb-v0)**: http://localhost:3000
  - 👨‍💼 **Интерфейс оператора**: http://localhost:3000/operator
  - 👤 **Интерфейс клиента**: http://localhost:3000/client
- **Scibox Mock API**: http://localhost:8001/docs

### 5. Публичный доступ через ngrok

Для **тестирования с командой** используйте ngrok:

```bash
# Установите ngrok (скачать с https://ngrok.com/download)

# Получите authtoken на https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_AUTHTOKEN

# Запустите туннели в отдельных терминалах
ngrok http 8000  # Backend
ngrok http 3000  # Frontend
```

**Результат:**
- 🌐 **Публичный backend**: `https://abc123.ngrok.io` 
- 🌐 **Публичный frontend**: `https://xyz789.ngrok.io`
- 👨‍💼 **Оператор**: `https://xyz789.ngrok.io/operator`
- 👤 **Клиент**: `https://xyz789.ngrok.io/client`

## 📋 Инструкция по использованию

### 👨‍💼 Для операторов поддержки

1. **Откройте интерфейс оператора**: `http://localhost:3000/operator`
2. **Выберите тикет** из списка или создайте новый
3. **Подключитесь к чату** нажав кнопку "Подключиться"
4. **Общайтесь с клиентом** в реальном времени:
   - Отправляйте сообщения (Enter или кнопка)
   - Используйте **Ctrl+Enter** для быстрой отправки
   - Просматривайте **галочки прочтения** ✓✓
5. **Используйте ИИ-помощь**:
   - Разверните **"Анализ сообщений клиента"** для детальной аналитики
   - Используйте **рекомендованные ответы** (сворачиваемая панель)
   - Отслеживайте **категории и тональность** каждого сообщения

### 👤 Для клиентов

1. **Откройте интерфейс клиента**: `http://localhost:3000/client`
2. **Создайте новую сессию** указав ваше имя и email
3. **Опишите проблему** - ИИ автоматически проанализирует запрос
4. **Общайтесь с оператором** когда он подключится к чату
5. **Оцените решение** после завершения обращения

### 🎯 ИИ-анализ в действии

**Для каждого сообщения клиента** система автоматически:

#### 📊 В панели анализа оператора:
- 🏷️ **Определяет категорию** (Техподдержка → Проблемы входа) 
- 📈 **Анализирует тональность** (Позитивная/Негативная/Нейтральная)
- 🔍 **Извлекает ключевые слова** ("пароль", "ошибка", "вход")
- 💯 **Показывает уверенность** ИИ в процентах (85% уверенность)
- 📝 **Нумерует сообщения** для удобства отслеживания

#### 💡 В рекомендациях:
- ✅ **Предлагает готовые ответы** на основе категории
- 🎯 **Адаптирует тон** ответа под настроение клиента
- 📚 **Использует базу знаний** для точных рекомендаций
- 🔄 **Обновляется в реальном времени** при новых сообщениях

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
                    │                 │
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

**Backend (FastAPI):**
```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск в режиме разработки
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend (Next.js):**
```bash
# Переход в папку фронтенда
cd frontend/vtb-v0

# Установка зависимостей
npm install

# Запуск в режиме разработки
npm run dev  # Запустится на http://localhost:3000
```

### Структура проекта

```
smart-support/
├── 🐍 Backend (FastAPI)
│   ├── main.py                      # Основной FastAPI сервер
│   ├── models.py                    # Pydantic модели данных
│   ├── websocket_manager.py         # WebSocket для real-time чата
│   └── services/                    # Бизнес-логика
│       ├── scibox_service.py        # Интеграция с Scibox ИИ
│       ├── knowledge_base.py        # База знаний с ответами
│       └── recommendation_engine.py # Генерация рекомендаций
│
├── ⚛️ Frontend (Next.js + React)
│   └── frontend/vtb-v0/
│       ├── app/                     # Next.js 15 App Router
│       │   ├── operator/page.tsx    # 👨‍💼 Интерфейс оператора
│       │   ├── client/page.tsx      # 👤 Интерфейс клиента
│       │   └── layout.tsx           # Общий layout
│       ├── components/              # React компоненты
│       │   ├── chat-area.tsx        # 💬 Компонент чата
│       │   ├── ticket-list.tsx      # 📋 Список тикетов
│       │   └── ui/                  # shadcn/ui компоненты
│       ├── lib/                     # Утилиты и типы
│       │   ├── types.ts             # TypeScript типы
│       │   └── websocket.ts         # WebSocket клиент
│       └── package.json             # NPM зависимости
│
├── 🗂️ Статические файлы
│   └── static/                      # Старые HTML интерфейсы
│       ├── operator.html            # Простой интерфейс оператора
│       └── client.html              # Простой интерфейс клиента
│
├── 🤖 Scibox Mock
│   └── scibox-mock/mock_scibox.py   # Эмуляция ML API
│
├── 🐳 DevOps
│   ├── docker-compose.yml          # Docker Compose
│   ├── Dockerfile                   # Backend Docker образ
│   └── requirements.txt             # Python зависимости
│
└── 📚 Документация
    └── README.md                    # Эта документация
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