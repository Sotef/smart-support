#!/bin/bash

# Smart Support Quick Start Script
echo "🚀 Запуск Smart Support системы..."

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и повторите попытку."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и повторите попытку."
    exit 1
fi

echo "✅ Docker и Docker Compose найдены"

# Создаем необходимые директории
mkdir -p logs data

# Запускаем сервисы
echo "📦 Запуск контейнеров..."
docker-compose up -d smart-support redis postgres scibox-mock

# Ожидаем запуска сервисов
echo "⏳ Ожидание запуска сервисов (30 сек)..."
sleep 30

# Проверяем статус
echo "📊 Проверка статуса сервисов..."
docker-compose ps

echo ""
echo "🎉 Smart Support система запущена!"
echo ""
echo "📱 Доступные сервисы:"
echo "   • Web-интерфейс: http://localhost:8000"
echo "   • API документация: http://localhost:8000/docs"
echo "   • Scibox Mock API: http://localhost:8001/docs"
echo ""
echo "🔍 Для просмотра логов: docker-compose logs -f"
echo "🛑 Для остановки: docker-compose down"