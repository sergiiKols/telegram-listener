import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
import requests

# Загрузить переменные окружения
load_dotenv()

# Создать директорию логов если её нет
os.makedirs('/app/logs', exist_ok=True)

# Настроить логирование
logging.basicConfig(
    filename='/app/logs/telethon.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получить переменные окружения
API_ID = int(os.getenv('TELEGRAM_API_ID', '94575'))
API_HASH = os.getenv('TELEGRAM_API_HASH', 'a3406de8d171bb422bb6ddf3d164e0ac')
PHONE = os.getenv('TELEGRAM_PHONE', '+79991234567')
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', '')

# Создать клиент Telethon
client = TelegramClient('session', API_ID, API_HASH)

async def send_to_webhook(message_data):
    """Отправить данные в n8n webhook"""
    if not N8N_WEBHOOK_URL:
        logger.warning("N8N_WEBHOOK_URL не установлен, данные не отправляются")
        return
    
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=message_data, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ Данные отправлены в n8n: {response.status_code}")
        else:
            logger.error(f"❌ Ошибка при отправке: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки: {str(e)}")

@client.on(events.NewMessage(incoming=True))
async def handle_message(event):
    """Обработать входящее сообщение"""
    try:
        sender = await event.get_sender()
        message_text = event.message.message
        
        logger.info(f"📨 Получено сообщение от {sender.first_name} ({sender.id}): {message_text}")
        
        # Подготовить данные для отправки
        message_data = {
            "sender_id": sender.id,
            "sender_name": sender.first_name or "Unknown",
            "sender_username": sender.username or "No username",
            "message": message_text,
            "timestamp": datetime.now().isoformat(),
            "message_id": event.message.id
        }
        
        # Отправить в n8n
        await send_to_webhook(message_data)
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {str(e)}")

async def start_listener():
    """Запустить слушатель"""
    try:
        logger.info("🚀 Запуск Telegram Listener...")
        await client.start(phone=PHONE)
        logger.info(f"✅ Подключено к Telegram аккаунту: {PHONE}")
        logger.info("👂 Слушаю входящие сообщения...")
        
        # Оставаться активным
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {str(e)}")
        raise

async def main():
    """Главная функция"""
    try:
        await start_listener()
    except KeyboardInterrupt:
        logger.info("🛑 Остановка приложения...")
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
