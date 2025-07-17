from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseActor(ABC):
    """Базовый класс для всех акторов системы"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_running = False
        logger.info(f"Инициализация актора: {self.name}")
    
    @abstractmethod
    async def handle_message(self, message: Dict[str, Any]) -> Any:
        """Обработка входящего сообщения"""
        pass
    
    async def initialize(self):
        """Инициализация актора при запуске"""
        self.is_running = True
        logger.info(f"Актор {self.name} запущен")
    
    async def shutdown(self):
        """Корректное завершение работы актора"""
        self.is_running = False
        logger.info(f"Актор {self.name} остановлен")