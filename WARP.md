# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project: Smart Support — FastAPI backend with a lightweight frontend, optional Docker Compose stack, and a mock Scibox service for NLP-like analysis.

Repository root: \\?\C:\Users\4ekwk\Downloads\smart-support

- Primary app entrypoint: app/main.py
- Frontend assets: static/
- Mock Scibox API: scibox-mock/mock_scibox.py
- Containerization: Dockerfile, docker-compose.yml

Commands you’ll use often

- Local setup (Windows PowerShell)

  ```pwsh path=null start=null
  # Create and activate virtual environment
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

  # Install dependencies
  pip install -r requirements.txt

  # Run FastAPI with auto-reload
  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

- Run only the mock Scibox service (without Docker)

  ```pwsh path=null start=null
  # In a separate shell if the app is running
  python scibox-mock\mock_scibox.py
  ```

- Docker build and run (single container)

  ```pwsh path=null start=null
  docker build -t smart-support:local .
  docker run --rm -p 8000:8000 --name smart-support-app smart-support:local
  ```

- Docker Compose

  ```pwsh path=null start=null
  # Core services: app + redis + postgres + scibox-mock
  docker-compose up -d smart-support redis postgres scibox-mock

  # Full stack (adds nginx, prometheus, grafana if configs are present)
  docker-compose up -d

  # Follow logs
  docker-compose logs -f smart-support

  # Rebuild images without cache
  docker-compose build --no-cache
  ```

- Health and quick checks

  ```pwsh path=null start=null
  # App health (PowerShell)
  iwr http://localhost:8000/health | select -ExpandProperty Content

  # Mock Scibox health
  iwr http://localhost:8001/health | select -ExpandProperty Content
  ```

- Example API call (analyze)

  ```pwsh path=null start=null
  $body = {
    request_id = "req_$(Get-Date -Format yyyyMMddHHmmss)"
    text       = "У меня не получается войти в личный кабинет. Пишет ошибка 404. Мой номер +7 (900) 123-45-67"
    customer_id= "client_001"
    channel    = "web"
  } | ConvertTo-Json

  irm -Method POST -Uri http://localhost:8000/api/analyze -ContentType 'application/json' -Body $body
  ```

Notes on linting and tests

- Lint/format: не настроено (ruff/flake8/black отсутствуют).
- Tests: добавлен pytest (requirements-dev.txt), минимальные тесты в папке tests/.

High-level architecture and data flow

- FastAPI application (app/main.py)
  - Initializes core services on startup: SciboxService, KnowledgeBaseService, RecommendationEngine, and WebSocketManager.
  - Serves the SPA-like static UI at / (static/index.html, static/app.js, static/style.css).
  - REST API:
    - POST /api/analyze: orchestrates text analysis via SciboxService, then enriches with knowledge-base lookups and recommendations; broadcasts an analysis_complete message over WebSocket.
    - POST /api/feedback: captures operator feedback for future improvements (kept in-memory).
    - GET /api/knowledge-base/search: lightweight search over synthetic knowledge articles.
    - GET /health: aggregates service health (Scibox and Knowledge Base).
  - WebSocket /ws/{client_id}: real-time channel for progress and result notifications. UI prefers WS; falls back to HTTP.

- Scibox integration (app/services/scibox_service.py)
  - Primary responsibility: entity extraction, classification, sentiment, and keyword extraction for support texts.
  - Tries to call a real Scibox endpoint at SCIBOX_URL (defaults to http://localhost:8001). If unavailable, falls back to synthetic analysis implemented in-process using regexes and simple heuristics.
  - Returns a normalized AnalysisResult consumed elsewhere in the app.

- Knowledge base and recommendations
  - KnowledgeBaseService (app/services/knowledge_base.py)
    - In-memory synthetic articles seeded at startup; supports keyword-in-title/tags/content matching with relevance scoring.
    - Provides category-scoped suggested responses.
  - RecommendationEngine (app/services/recommendation_engine.py)
    - Combines Scibox analysis + knowledge base:
      - Finds relevant articles by text, keywords, and category.
      - Produces suggested responses (adapts for negative sentiment; can prepend entity-aware messages).
      - Determines actions for the operator based on category, entities, and sentiment.
      - Heuristically sets a priority (e.g., HIGH for complaint with negative sentiment, or technical with error codes).
      - Emits human-readable “insights” (e.g., low confidence, negative tone, many entities).

- Real-time messaging (app/websocket_manager.py)
  - Tracks active connections per client_id, supports broadcast and per-client messages, and optional grouping.
  - API handlers push analysis_complete updates; analyze_and_notify also sends a per-client analysis_result message.

- Persistence
  - app/database.py contains an in-memory synthetic database and a FastAPI dependency stub; no real DB session is wired despite postgres being available in docker-compose. Data is ephemeral across process restarts.

- Frontend (static/)
  - static/app.js bootstraps a WebSocket to /ws/{client_id}; if WS is closed/unavailable, falls back to HTTP POST /api/analyze.
  - Renders analysis results, recommended actions, insights, and suggested responses; provides a feedback modal to POST /api/feedback.

New frontend (branch front_main)

- Исходники фронтенда из rezniki/Support-dashboard добавлены в каталог frontend/Support-dashboard (Vite + React).
- Сборка и публикация в static/:

  ```pwsh path=null start=null
  # Требуется установленный Node.js (https://nodejs.org)
  pwsh ./scripts/build_front.ps1
  ```

- Скрипт выполнит npm ci && npm run build в frontend/Support-dashboard и скопирует содержимое dist/ в static/.
- Бэкенд продолжает раздавать статику из каталога static/ без изменений кода.

- Containerization and services
  - Dockerfile builds a Python 3.11-slim image, installs requirements, copies app and static, runs uvicorn.
  - docker-compose.yml optionally orchestrates:
    - smart-support (app) with ENV vars and healthcheck
    - redis (queues/cache, not actively used in code paths yet)
    - postgres (not currently used by the running app logic)
    - scibox-mock (FastAPI mock of Scibox)
    - nginx (reverse proxy, optional)
    - prometheus/grafana (monitoring, optional)
  - Volumes are mounted for logs/data; app healthcheck queries /health.

Configuration highlights

- Important environment variables (see docker-compose.yml, .env.example):
  - ENVIRONMENT, LOG_LEVEL
  - SCIBOX_URL (e.g., http://scibox:8001 in Compose). Загружается из .env (load_dotenv), используется при инициализации SciboxService.
  - SCIBOX_API_KEY (опционально для реального Scibox). Если задан, передается в заголовке Authorization: Bearer {token} при вызове /api/analyze реального Scibox.
  - REDIS_URL, DATABASE_URL (заданы, но в текущей логике не используются)
- Скопируйте .env.example в .env и при необходимости измените значения.

Productivity shortcuts

Tests

Secrets (безопасная настройка API-ключа)

- Установите API-ключ в переменную окружения (не вставляйте значение в команды напрямую):

  ```pwsh path=null start=null
  # Сохранить ключ только на текущую сессию
  $Env:SCIBOX_API_KEY = {{SCIBOX_API_KEY}}

  # Для постоянного сохранения ключа в Windows (перезапустите терминал после выполнения):
  setx SCIBOX_API_KEY "{{SCIBOX_API_KEY}}"
  ```

- Приложение автоматически подхватывает ключ из .env/переменных окружения и добавляет заголовок Authorization к запросам на реальный Scibox.

- Установка dev-зависимостей (pytest):

  ```pwsh path=null start=null
  pip install -r requirements-dev.txt
  ```

- Запуск всех тестов:

  ```pwsh path=null start=null
  pytest
  ```

- Запуск одного теста:

  ```pwsh path=null start=null
  pytest tests/test_health.py::test_health_endpoint -q
  ```

- Start local dev quickly (PowerShell):

  ```pwsh path=null start=null
  python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; \
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

- Core Compose stack for end-to-end testing with the mock:

  ```pwsh path=null start=null
  docker-compose up -d smart-support redis postgres scibox-mock
  ```

- Inspect recent app logs:

  ```pwsh path=null start=null
  docker-compose logs --tail=200 -f smart-support
  ```

References from README.md

- Web UI: http://localhost:8000
- API docs: http://localhost:8000/docs
- Scibox Mock API: http://localhost:8001/docs
- Optional monitoring endpoints if enabled in Compose:
  - Grafana: http://localhost:3000 (credentials per README)
  - Prometheus: http://localhost:9090
