@echo off
title Smart Support Launcher
color 0A

echo =============================================
echo    Smart Support - Запуск сервисов
echo =============================================
echo.

echo ✅ Запускаем Backend API на порту 8000...
start "Backend-API" cmd /k "title Backend API && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo ✅ Запускаем Frontend vtb-v0 на порту 3000...
start "Frontend-vtb-v0" cmd /k "title Frontend vtb-v0 && cd frontend/vtb-v0 && npm run dev"

echo.
echo =============================================
echo    Smart Support запущен! 🚀
echo =============================================
echo.
echo 📋 ЛОКАЛЬНЫЕ АДРЕСА:
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo.
echo 🌐 ИНТЕРФЕЙСЫ:
echo   👨‍💼 Оператор: http://localhost:3000/operator
echo   👤 Клиент:    http://localhost:3000/client
echo.
echo 🎯 ВОЗМОЖНОСТИ:
echo   ✓ Реальный чат с галочками ✓✓
echo   ✓ ИИ-анализ сообщений
echo   ✓ Умные рекомендации
echo   ✓ Панель аналитики
echo.
pause