import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

from config.settings import TELEGRAM_BOT_TOKEN, TYPING_DELAY, USER_MESSAGES, USE_JSON_MODE, DEFAULT_MODE
from services.deepseek_service import deepseek_service
from events.base_event import BaseEvent

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ChimeraTelegramBot:
    """Telegram бот Химеры - прототип будущего UserSessionActor"""
    
    def __init__(self):
        self.application = None
        self.is_running = False
    
    async def log_event(self, event_type: str, user_id: int, data: dict):
        """Логирование событий - прототип Event Sourcing"""
        event = BaseEvent(
            event_type=event_type,
            user_id=user_id,
            data=data
        )
        logger.info(f"Event: {event.json()}")
        # В будущем здесь будет сохранение в Event Store
    
    async def send_typing_action(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Отправка индикатора печати"""
        while self.is_typing:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(TYPING_DELAY)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка входящих сообщений - прототип UserSessionActor координации
        """
        try:
            # Извлекаем данные пользователя
            user_id = update.message.from_user.id
            username = update.message.from_user.username or "unknown"
            message_text = update.message.text
            chat_id = update.effective_chat.id
            
            # Логируем входящее сообщение
            await self.log_event(
                "user_message",
                user_id,
                {
                    "text": message_text,
                    "username": username,
                    "chat_id": chat_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Запускаем индикатор печати
            self.is_typing = True
            typing_task = asyncio.create_task(
                self.send_typing_action(context, chat_id)
            )
            
            try:
                # Получаем ответ от DeepSeek с JSON обработкой
                response = await deepseek_service.ask_deepseek(
                    message_text,
                    user_id=user_id,
                    use_json=USE_JSON_MODE,  # Берем из конфигурации
                    mode=DEFAULT_MODE  # Берем из конфигурации
                )
                
                # Останавливаем индикатор печати
                self.is_typing = False
                await typing_task
                
                # Отправляем ответ
                await update.message.reply_text(response)
                
                # Логируем ответ бота
                await self.log_event(
                    "bot_response",
                    user_id,
                    {
                        "text": response,
                        "chat_id": chat_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
            except Exception as e:
                self.is_typing = False
                logger.error(f"Error in message processing: {e}")
                await update.message.reply_text(USER_MESSAGES["error_processing"])
                
        except Exception as e:
            logger.error(f"Critical error in handle_message: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка команды /start"""
        user_id = update.message.from_user.id
        
        await self.log_event(
            "command_start",
            user_id,
            {"timestamp": datetime.utcnow().isoformat()}
        )
        
        await update.message.reply_text(USER_MESSAGES["welcome"])
    
    async def initialize(self):
        """Инициализация бота"""
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Регистрация обработчиков
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        self.is_running = True
        logger.info("Telegram bot initialized")
    
    async def run(self):
        """Запуск бота"""
        await self.initialize()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Bot started polling")
    
    async def shutdown(self):
        """Остановка бота"""
        if self.application:
            await self.application.stop()
        self.is_running = False
        logger.info("Bot stopped")


# Глобальный экземпляр бота
telegram_bot = ChimeraTelegramBot()