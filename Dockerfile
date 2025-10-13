# Smart Support - ИИ-ассистент службы поддержки
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY app/ ./app/
COPY static/ ./static/

# Создаем непривилегированного пользователя
RUN groupadd -r smartsupport && useradd -r -g smartsupport smartsupport

# Создаем директории для логов и данных
RUN mkdir -p /app/logs /app/data && \
    chown -R smartsupport:smartsupport /app

# Переключаемся на непривилегированного пользователя
USER smartsupport

# Открываем порт
EXPOSE 8000

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Проверка здоровья контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Команда запуска
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]