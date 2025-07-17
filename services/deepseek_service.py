import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, API_TIMEOUT, USER_MESSAGES
from config.prompts import get_system_prompt
from config.api_params import get_api_params
from services.response_processor import response_processor


logger = logging.getLogger(__name__)


class DeepSeekService:
    """Сервис для работы с DeepSeek API"""
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
    
    async def ask_deepseek(
            self, 
            message: str, 
            user_id: Optional[int] = None,
            use_json: bool = False,
            mode: str = "default"
        ) -> str:
            """
            Отправить запрос к DeepSeek API
            
            Args:
                message: Сообщение пользователя
                user_id: ID пользователя для персонализации
                use_json: Использовать JSON режим
                mode: Режим работы
            
            Returns:
                Обработанный ответ от модели
            """
            try:
                # Статистика использования режимов
                logger.info(f"DeepSeek request - mode: {mode}, json: {use_json}, user: {user_id}")
                
                # Получаем параметры и промпт для режима
                params = get_api_params(mode)
                system_prompt = get_system_prompt(mode, use_json)
                
                # Формируем запрос
                request_data = {
                    **params,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ]
                }
                
                # Добавляем JSON режим если нужно
                if use_json:
                    request_data["response_format"] = {"type": "json_object"}
                
                # Отправляем запрос с retry логикой
                for attempt in range(3):
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                DEEPSEEK_API_URL,
                                headers=self.headers,
                                json=request_data,
                                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                            ) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    raw_response = data["choices"][0]["message"]["content"]
                                    
                                    # Обрабатываем ответ через процессор
                                    processed_response = await response_processor.process_response(
                                        raw_response, 
                                        mode=mode, 
                                        use_json=use_json
                                    )
                                    
                                    return processed_response
                                else:
                                    error_text = await response.text()
                                    logger.error(f"DeepSeek API error: {response.status} - {error_text}")
                                    
                                    # При ошибке JSON режима пробуем обычный
                                    if use_json and attempt == 0:
                                        logger.info("JSON mode failed, falling back to normal mode")
                                        use_json = False
                                        request_data.pop("response_format", None)
                                        system_prompt = get_system_prompt(mode, use_json=False)
                                        request_data["messages"][0]["content"] = system_prompt
                                        continue
                                    
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout on attempt {attempt + 1}")
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)
                        continue
                        
                    except Exception as e:
                        logger.error(f"Request error on attempt {attempt + 1}: {e}")
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)
                        continue
                
                # Если все попытки неудачны
                from config.settings import USER_MESSAGES
                return USER_MESSAGES["service_unavailable"]
                
            except Exception as e:
                logger.error(f"DeepSeek service error: {e}")
                from config.settings import USER_MESSAGES
                return USER_MESSAGES["critical_error"]


# Глобальный экземпляр сервиса
deepseek_service = DeepSeekService()