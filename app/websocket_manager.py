import asyncio
import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Менеджер WebSocket соединений для real-time уведомлений
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_groups: Dict[str, List[str]] = {}  # Группы соединений

    async def connect(self, websocket: WebSocket, client_id: str):
        """Подключение нового клиента"""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            logger.info(f"WebSocket подключение установлено: {client_id}")
            
            # Отправляем подтверждение подключения
            await self.send_personal_message({
                "type": "connection_established",
                "client_id": client_id,
                "message": "Подключение к Smart Support системе установлено"
            }, client_id)
            
        except Exception as e:
            logger.error(f"Ошибка подключения WebSocket {client_id}: {str(e)}")

    async def disconnect(self, client_id: str):
        """Отключение клиента"""
        try:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                logger.info(f"WebSocket отключен: {client_id}")
                
                # Удаляем из всех групп
                for group_name, members in self.connection_groups.items():
                    if client_id in members:
                        members.remove(client_id)
                        
        except Exception as e:
            logger.error(f"Ошибка отключения WebSocket {client_id}: {str(e)}")

    async def send_personal_message(self, message: dict, client_id: str):
        """Отправка личного сообщения клиенту"""
        try:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message, ensure_ascii=False, default=str))
                logger.debug(f"Сообщение отправлено клиенту {client_id}")
            else:
                logger.warning(f"Клиент {client_id} не найден среди активных соединений")
                
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения клиенту {client_id}: {str(e)}")
            # Удаляем неактивное соединение
            if client_id in self.active_connections:
                del self.active_connections[client_id]

    async def broadcast(self, message: dict):
        """Рассылка сообщения всем подключенным клиентам"""
        try:
            if not self.active_connections:
                logger.debug("Нет активных WebSocket соединений для рассылки")
                return
                
            # Создаем копию списка соединений для избежания изменения во время итерации
            connections_copy = list(self.active_connections.items())
            
            for client_id, websocket in connections_copy:
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False, default=str))
                except Exception as e:
                    logger.error(f"Ошибка рассылки клиенту {client_id}: {str(e)}")
                    # Удаляем неактивное соединение
                    if client_id in self.active_connections:
                        del self.active_connections[client_id]
            
            logger.info(f"Сообщение отправлено {len(connections_copy)} клиентам")
            
        except Exception as e:
            logger.error(f"Ошибка рассылки сообщения: {str(e)}")

    async def send_to_group(self, message: dict, group_name: str):
        """Отправка сообщения группе клиентов"""
        try:
            if group_name not in self.connection_groups:
                logger.warning(f"Группа {group_name} не существует")
                return
                
            group_members = self.connection_groups[group_name].copy()
            
            for client_id in group_members:
                await self.send_personal_message(message, client_id)
            
            logger.info(f"Сообщение отправлено группе {group_name} ({len(group_members)} клиентов)")
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения группе {group_name}: {str(e)}")

    def add_to_group(self, client_id: str, group_name: str):
        """Добавление клиента в группу"""
        try:
            if client_id in self.active_connections:
                if group_name not in self.connection_groups:
                    self.connection_groups[group_name] = []
                    
                if client_id not in self.connection_groups[group_name]:
                    self.connection_groups[group_name].append(client_id)
                    logger.info(f"Клиент {client_id} добавлен в группу {group_name}")
                    
        except Exception as e:
            logger.error(f"Ошибка добавления клиента {client_id} в группу {group_name}: {str(e)}")

    def remove_from_group(self, client_id: str, group_name: str):
        """Удаление клиента из группы"""
        try:
            if (group_name in self.connection_groups and 
                client_id in self.connection_groups[group_name]):
                self.connection_groups[group_name].remove(client_id)
                logger.info(f"Клиент {client_id} удален из группы {group_name}")
                
        except Exception as e:
            logger.error(f"Ошибка удаления клиента {client_id} из группы {group_name}: {str(e)}")

    async def send_analysis_update(self, client_id: str, status: str, progress: int = None, data: dict = None):
        """Отправка обновления статуса анализа"""
        message = {
            "type": "analysis_update",
            "status": status,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        if progress is not None:
            message["progress"] = progress
            
        if data:
            message["data"] = data
            
        await self.send_personal_message(message, client_id)

    async def send_recommendation_update(self, client_id: str, recommendations: dict):
        """Отправка обновления рекомендаций"""
        message = {
            "type": "recommendation_update",
            "recommendations": recommendations,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.send_personal_message(message, client_id)

    async def send_system_notification(self, notification_type: str, message_text: str, level: str = "info"):
        """Отправка системного уведомления всем клиентам"""
        message = {
            "type": "system_notification",
            "notification_type": notification_type,
            "message": message_text,
            "level": level,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.broadcast(message)

    def get_connection_stats(self) -> dict:
        """Получение статистики соединений"""
        return {
            "active_connections": len(self.active_connections),
            "groups": {name: len(members) for name, members in self.connection_groups.items()},
            "connected_clients": list(self.active_connections.keys())
        }

    async def ping_all_connections(self):
        """Проверка всех активных соединений"""
        try:
            if not self.active_connections:
                return
                
            ping_message = {
                "type": "ping",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Проверяем каждое соединение
            disconnected_clients = []
            
            for client_id, websocket in self.active_connections.items():
                try:
                    await websocket.send_text(json.dumps(ping_message))
                except Exception as e:
                    logger.warning(f"Соединение {client_id} недоступно: {str(e)}")
                    disconnected_clients.append(client_id)
            
            # Удаляем недоступные соединения
            for client_id in disconnected_clients:
                await self.disconnect(client_id)
                
            logger.info(f"Проверка соединений завершена. Активных: {len(self.active_connections)}")
            
        except Exception as e:
            logger.error(f"Ошибка проверки соединений: {str(e)}")

    async def cleanup_inactive_connections(self):
        """Очистка неактивных соединений"""
        try:
            await self.ping_all_connections()
            
            # Очистка пустых групп
            empty_groups = [name for name, members in self.connection_groups.items() if not members]
            for group_name in empty_groups:
                del self.connection_groups[group_name]
                logger.info(f"Удалена пустая группа: {group_name}")
                
        except Exception as e:
            logger.error(f"Ошибка очистки соединений: {str(e)}")