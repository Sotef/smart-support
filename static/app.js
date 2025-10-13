// Smart Support Frontend Application
class SmartSupportApp {
    constructor() {
        this.websocket = null;
        this.clientId = this.generateClientId();
        this.currentRequestId = null;
        this.analysisInProgress = false;
        
        this.initializeApp();
    }

    generateClientId() {
        return 'client_' + Math.random().toString(36).substr(2, 9);
    }

    initializeApp() {
        console.log('Initializing Smart Support App...');
        
        // Инициализация WebSocket
        this.connectWebSocket();
        
        // Привязка событий
        this.bindEvents();
        
        // Загрузка тестовых примеров
        this.loadExamples();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.clientId}`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = (event) => {
                console.log('WebSocket connected');
                this.updateConnectionStatus(true);
                this.showNotification('Подключение к системе установлено', 'success');
            };
            
            this.websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            };
            
            this.websocket.onclose = (event) => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                
                // Попытка переподключения через 3 секунды
                setTimeout(() => {
                    this.connectWebSocket();
                }, 3000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.updateConnectionStatus(false);
        }
    }

    bindEvents() {
        // Форма анализа запроса
        document.getElementById('supportRequestForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.analyzeRequest();
        });

        // Кнопки копирования ответов
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('copy-response-btn')) {
                this.copyResponseToClipboard(e.target.dataset.response);
            }
        });

        // Модальное окно статистики
        document.getElementById('statsModal').addEventListener('show.bs.modal', () => {
            this.loadStatistics();
        });

        // Форма обратной связи
        document.getElementById('submitFeedback').addEventListener('click', () => {
            this.submitFeedback();
        });

        // Клики по вариантам ответов
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('response-option')) {
                this.selectResponse(e.target);
            }
        });
    }

    handleWebSocketMessage(message) {
        console.log('WebSocket message:', message);
        
        switch (message.type) {
            case 'connection_established':
                console.log('Connection established:', message.client_id);
                break;
                
            case 'analysis_complete':
                this.displayAnalysisResults(message.data);
                break;
                
            case 'analysis_update':
                this.updateAnalysisProgress(message.status, message.progress);
                break;
                
            case 'recommendation_update':
                this.displayRecommendations(message.recommendations);
                break;
                
            case 'system_notification':
                this.showNotification(message.message, message.level);
                break;
                
            case 'ping':
                // Отправляем pong в ответ на ping
                this.websocket.send(JSON.stringify({type: 'pong'}));
                break;
                
            default:
                console.log('Unknown message type:', message.type);
        }
    }

    async analyzeRequest() {
        const requestText = document.getElementById('requestText').value.trim();
        const customerInfo = document.getElementById('customerInfo').value.trim();
        const channel = document.getElementById('channel').value;
        
        if (!requestText) {
            this.showNotification('Введите текст обращения', 'warning');
            return;
        }

        this.currentRequestId = this.generateRequestId();
        this.analysisInProgress = true;
        
        // Показываем прогресс
        this.showAnalysisProgress();
        
        const requestData = {
            request_id: this.currentRequestId,
            text: requestText,
            customer_id: customerInfo || null,
            channel: channel,
            metadata: {
                timestamp: new Date().toISOString(),
                user_agent: navigator.userAgent
            }
        };

        try {
            // Отправляем через WebSocket для real-time обновлений
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'analyze_request',
                    data: requestData
                }));
            } else {
                // Fallback: прямой HTTP запрос
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    this.displayAnalysisResults(result);
                } else {
                    throw new Error('Ошибка анализа запроса');
                }
            }
            
        } catch (error) {
            console.error('Analysis error:', error);
            this.showNotification('Ошибка при анализе запроса', 'error');
            this.hideAnalysisProgress();
            this.analysisInProgress = false;
        }
    }

    generateRequestId() {
        return 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
    }

    showAnalysisProgress() {
        const progressDiv = document.getElementById('analysisProgress');
        const analyzeBtn = document.getElementById('analyzeBtn');
        
        progressDiv.style.display = 'block';
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="loading-spinner"></span> Анализ...';
        
        // Симуляция прогресса
        this.simulateProgress();
    }

    simulateProgress() {
        const progressBar = document.querySelector('#analysisProgress .progress-bar');
        const statusText = document.getElementById('analysisStatus');
        
        let progress = 0;
        const steps = [
            { progress: 20, status: 'Подключение к Scibox...' },
            { progress: 40, status: 'Извлечение сущностей...' },
            { progress: 60, status: 'Классификация запроса...' },
            { progress: 80, status: 'Поиск в базе знаний...' },
            { progress: 90, status: 'Генерация рекомендаций...' }
        ];
        
        let stepIndex = 0;
        const interval = setInterval(() => {
            if (stepIndex < steps.length && !this.analysisInProgress === false) {
                const step = steps[stepIndex];
                progressBar.style.width = step.progress + '%';
                statusText.textContent = step.status;
                stepIndex++;
            } else {
                clearInterval(interval);
            }
        }, 800);
    }

    hideAnalysisProgress() {
        const progressDiv = document.getElementById('analysisProgress');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const progressBar = document.querySelector('#analysisProgress .progress-bar');
        
        progressDiv.style.display = 'none';
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="fas fa-search me-2"></i>Анализировать запрос';
        progressBar.style.width = '0%';
        
        this.analysisInProgress = false;
    }

    displayAnalysisResults(result) {
        console.log('Displaying analysis results:', result);
        
        this.hideAnalysisProgress();
        
        const analysisDiv = document.getElementById('analysisResults');
        const recommendationsDiv = document.getElementById('recommendations');
        const responsesDiv = document.getElementById('suggestedResponses');
        
        // Результаты анализа
        analysisDiv.innerHTML = this.renderAnalysisResults(result);
        analysisDiv.classList.add('fade-in');
        
        // Рекомендации
        if (result.recommendations) {
            recommendationsDiv.innerHTML = this.renderRecommendations(result.recommendations);
            recommendationsDiv.classList.add('slide-in-left');
        }
        
        // Предлагаемые ответы
        if (result.suggested_responses && result.suggested_responses.length > 0) {
            responsesDiv.innerHTML = this.renderSuggestedResponses(result.suggested_responses);
            responsesDiv.classList.add('fade-in');
        }
        
        // Показываем кнопку обратной связи
        this.showFeedbackButton();
    }

    renderAnalysisResults(result) {
        const categoryClass = `category-${result.classification.replace('_', '-')}`;
        const confidenceClass = result.confidence > 0.7 ? 'success' : result.confidence > 0.4 ? 'warning' : 'danger';
        const sentimentIcon = this.getSentimentIcon(result.sentiment);
        const priorityClass = `priority-${result.priority?.toLowerCase() || 'medium'}`;
        
        let html = `
            <div class="analysis-item ${priorityClass}">
                <h6><i class="fas fa-tag me-2"></i>Категория</h6>
                <span class="badge ${categoryClass} me-2">${this.getCategoryName(result.classification)}</span>
                <span class="badge bg-${confidenceClass} confidence-badge">${Math.round(result.confidence * 100)}% уверенности</span>
            </div>
        `;
        
        // Тональность
        if (result.sentiment !== undefined && result.sentiment !== null) {
            html += `
                <div class="analysis-item">
                    <h6><i class="fas fa-smile me-2"></i>Тональность</h6>
                    <span class="${this.getSentimentClass(result.sentiment)}">
                        ${sentimentIcon} ${this.getSentimentText(result.sentiment)}
                    </span>
                </div>
            `;
        }
        
        // Сущности
        if (result.entities && result.entities.length > 0) {
            html += `
                <div class="analysis-item">
                    <h6><i class="fas fa-search me-2"></i>Извлеченные сущности</h6>
                    <div>
                        ${result.entities.map(entity => 
                            `<span class="badge bg-info entity-badge me-1" title="Уверенность: ${Math.round(entity.confidence * 100)}%">
                                ${entity.type}: ${entity.text}
                            </span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        
        // Ключевые слова
        if (result.keywords && result.keywords.length > 0) {
            html += `
                <div class="analysis-item">
                    <h6><i class="fas fa-key me-2"></i>Ключевые слова</h6>
                    <div>
                        ${result.keywords.map(keyword => 
                            `<span class="badge bg-secondary me-1">${keyword}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        
        return html;
    }

    renderRecommendations(recommendations) {
        let html = '';
        
        // Релевантные статьи
        if (recommendations.relevant_articles && recommendations.relevant_articles.length > 0) {
            html += `
                <h6><i class="fas fa-book me-2"></i>Релевантные статьи базы знаний</h6>
                ${recommendations.relevant_articles.map(article => `
                    <div class="recommendation-card">
                        <div class="recommendation-title">${article.title}</div>
                        <div class="recommendation-content">${article.content.substring(0, 150)}...</div>
                        <small class="relevance-score">Релевантность: ${Math.round(article.relevance_score * 100)}%</small>
                    </div>
                `).join('')}
            `;
        }
        
        // Действия
        if (recommendations.actions && recommendations.actions.length > 0) {
            html += `
                <h6 class="mt-3"><i class="fas fa-tasks me-2"></i>Рекомендуемые действия</h6>
                ${recommendations.actions.map(action => `
                    <div class="action-item">${action}</div>
                `).join('')}
            `;
        }
        
        // Инсайты
        if (recommendations.insights && recommendations.insights.length > 0) {
            html += `
                <h6 class="mt-3"><i class="fas fa-lightbulb me-2"></i>Дополнительные инсайты</h6>
                ${recommendations.insights.map(insight => `
                    <div class="insight-item ${this.getInsightClass(insight)}">${insight}</div>
                `).join('')}
            `;
        }
        
        return html || '<p class="text-muted">Рекомендации не найдены</p>';
    }

    renderSuggestedResponses(responses) {
        return `
            <div class="mb-3">
                <small class="text-muted">Нажмите на вариант ответа для выбора</small>
            </div>
            ${responses.map((response, index) => `
                <div class="response-option" data-response="${response}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">${response}</div>
                        <button class="btn btn-outline-primary btn-sm copy-response-btn ms-2" 
                                data-response="${response}" title="Копировать">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
            `).join('')}
        `;
    }

    selectResponse(element) {
        // Убираем выделение с других ответов
        document.querySelectorAll('.response-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        
        // Выделяем выбранный
        element.classList.add('selected');
        
        // Показываем кнопку обратной связи
        this.showFeedbackButton();
    }

    copyResponseToClipboard(response) {
        navigator.clipboard.writeText(response).then(() => {
            this.showNotification('Ответ скопирован в буфер обмена', 'success');
        }).catch(() => {
            this.showNotification('Ошибка копирования', 'error');
        });
    }

    showFeedbackButton() {
        // Добавляем кнопку обратной связи, если её еще нет
        const responsesDiv = document.getElementById('suggestedResponses');
        if (!responsesDiv.querySelector('.feedback-btn')) {
            const feedbackBtn = document.createElement('button');
            feedbackBtn.className = 'btn btn-outline-secondary btn-sm mt-3 feedback-btn';
            feedbackBtn.innerHTML = '<i class="fas fa-comment me-2"></i>Оставить отзыв';
            feedbackBtn.onclick = () => {
                const modal = new bootstrap.Modal(document.getElementById('feedbackModal'));
                modal.show();
            };
            responsesDiv.appendChild(feedbackBtn);
        }
    }

    async submitFeedback() {
        const quality = document.querySelector('input[name="quality"]:checked')?.value;
        const responseUsed = document.getElementById('responseUsed').checked;
        const comments = document.getElementById('comments').value;
        
        if (!quality) {
            this.showNotification('Пожалуйста, оцените качество рекомендаций', 'warning');
            return;
        }
        
        const feedbackData = {
            request_id: this.currentRequestId,
            recommendation_quality: parseInt(quality),
            response_used: responseUsed,
            operator_comments: comments || null
        };
        
        try {
            const response = await fetch('/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(feedbackData)
            });
            
            if (response.ok) {
                this.showNotification('Спасибо за обратную связь!', 'success');
                
                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('feedbackModal'));
                modal.hide();
                
                // Очищаем форму
                document.getElementById('feedbackForm').reset();
            } else {
                throw new Error('Ошибка отправки обратной связи');
            }
            
        } catch (error) {
            console.error('Feedback error:', error);
            this.showNotification('Ошибка отправки обратной связи', 'error');
        }
    }

    async loadStatistics() {
        const statsContent = document.getElementById('statsContent');
        
        try {
            const response = await fetch('/health');
            const data = await response.json();
            
            statsContent.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <div class="stat-card">
                            <div class="stat-number">${data.status === 'healthy' ? '✓' : '✗'}</div>
                            <div class="stat-label">Статус системы</div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="stat-card">
                            <div class="stat-number">${data.services?.scibox?.status || 'N/A'}</div>
                            <div class="stat-label">Статус Scibox</div>
                        </div>
                    </div>
                </div>
                <div class="mt-3">
                    <h6>Сервисы:</h6>
                    <ul class="list-group">
                        ${Object.entries(data.services || {}).map(([service, status]) => `
                            <li class="list-group-item d-flex justify-content-between">
                                <span>${service}</span>
                                <span class="badge bg-${status.status === 'healthy' || status.status === 'synthetic' ? 'success' : 'danger'}">
                                    ${status.status}
                                </span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
            
        } catch (error) {
            console.error('Stats error:', error);
            statsContent.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Ошибка загрузки статистики
                </div>
            `;
        }
    }

    loadExamples() {
        // Добавляем примеры запросов для тестирования
        const examples = [
            "У меня не получается войти в личный кабинет. Пишет ошибка 404. Мой номер телефона +7 (900) 123-45-67",
            "Здравствуйте! С моего счета 4276 1234 5678 9012 списали 5000 рублей, но я не делал покупок. Что делать?",
            "Добрый день! Хочу подключить новый тарифный план. Можно ли это сделать онлайн?",
            "Очень недоволен качеством обслуживания! Вчера обратился в офис, никто не помог. Требую разбирательства!"
        ];
        
        // Добавляем кнопки с примерами (можно добавить в интерфейс по желанию)
        console.log('Available examples:', examples);
    }

    // Вспомогательные методы
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connectionStatus');
        if (connected) {
            statusElement.innerHTML = '<i class="fas fa-circle text-success"></i> Подключено';
        } else {
            statusElement.innerHTML = '<i class="fas fa-circle text-danger"></i> Отключено';
        }
    }

    showNotification(message, type = 'info') {
        const toast = document.getElementById('notificationToast');
        const toastMessage = document.getElementById('toastMessage');
        
        toastMessage.textContent = message;
        
        // Меняем стиль в зависимости от типа
        const toastHeader = toast.querySelector('.toast-header');
        toastHeader.className = `toast-header bg-${type === 'error' ? 'danger' : type} text-${type === 'warning' ? 'dark' : 'white'}`;
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }

    getCategoryName(category) {
        const names = {
            'technical': 'Техническая проблема',
            'billing': 'Биллинг',
            'account': 'Аккаунт',
            'complaint': 'Жалоба',
            'general': 'Общий вопрос',
            'feature_request': 'Запрос функции'
        };
        return names[category] || category;
    }

    getSentimentIcon(sentiment) {
        if (sentiment > 0.3) return '😊';
        if (sentiment < -0.3) return '😟';
        return '😐';
    }

    getSentimentClass(sentiment) {
        if (sentiment > 0.3) return 'sentiment-positive';
        if (sentiment < -0.3) return 'sentiment-negative';
        return 'sentiment-neutral';
    }

    getSentimentText(sentiment) {
        if (sentiment > 0.3) return `Позитивная (${Math.round(sentiment * 100)}%)`;
        if (sentiment < -0.3) return `Негативная (${Math.round(Math.abs(sentiment) * 100)}%)`;
        return 'Нейтральная';
    }

    getInsightClass(insight) {
        if (insight.includes('⚠️')) return 'insight-warning';
        if (insight.includes('😟')) return 'insight-warning';
        if (insight.includes('😊')) return 'insight-success';
        return 'insight-info';
    }
}

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.smartSupport = new SmartSupportApp();
});