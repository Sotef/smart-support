@echo off
echo 🚀 Запуск Smart Support системы...

REM Проверяем наличие Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker не установлен. Установите Docker Desktop и повторите попытку.
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose не установлен. Установите Docker Desktop и повторите попытку.
    pause
    exit /b 1
)

echo ✅ Docker и Docker Compose найдены

REM Создаем необходимые директории
if not exist "logs" mkdir logs
if not exist "data" mkdir data

REM Запускаем сервисы
echo 📦 Запуск контейнеров...
docker-compose up -d smart-support redis postgres scibox-mock

REM Ожидаем запуска сервисов
echo ⏳ Ожидание запуска сервисов (30 сек)...
timeout /t 30 /nobreak >nul

REM Проверяем статус
echo 📊 Проверка статуса сервисов...
docker-compose ps

echo.
echo 🎉 Smart Support система запущена!
echo.
echo 📱 Доступные сервисы:
echo    • Web-интерфейс: http://localhost:8000
echo    • API документация: http://localhost:8000/docs
echo    • Scibox Mock API: http://localhost:8001/docs
echo.
echo 🔍 Для просмотра логов: docker-compose logs -f
echo 🛑 Для остановки: docker-compose down
echo.
pause