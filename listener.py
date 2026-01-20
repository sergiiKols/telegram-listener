import asyncio
import logging
import os
import sys
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import requests
from dotenv import load_dotenv
from flask import Flask
import threading

# Загрузить переменные окружения
load_dotenv()

# Flask приложение для health check
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return {'status': 'ok'}, 200

def run_flask():
    """Запустить Flask в отдельном потоке"""
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)

# Конфигурация логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/telethon.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Telegram credentials
API_ID = int(os.getenv('TELEGRAM_API_ID', '0'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
PHONE = os.getenv('TELEGRAM_PHONE', '')

# n8n webhook
N8N_WEBHOOK = os.getenv('N8N_WEBHOOK_URL', '')

# Session file (в папке volumes)
SESSION_FILE = '/app/sessions/telegram_session'

client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):
    """
    Обработка входящих сообщений
    """
    try:
        # Пропустить сообщения из групп (только личные DM)
        if event.is_group or event.is_channel:
            return
        
        # Получить отправителя и текст
        message = event.message
        sender = await event.get_sender()
        
        logger.info(f"📨 Сообщение от {sender.first_name} (ID: {sender.id}): {message.text}")
        
        # Отправить в n8n для анализа
        payload = {
            'sender_id': sender.id,
            'sender_name': sender.first_name,
            'sender_username': sender.username or 'N/A',
            'message': message.text,
            'timestamp': message.date.isoformat() if message.date else None,
            'message_id': message.id
        }
        
        try:
            response = requests.post(
                N8N_WEBHOOK,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Отправлено в n8n успешно (статус: {response.status_code})")
            else:
                logger.warning(f"⚠️  n8n ответил со статусом: {response.status_code}")
                logger.debug(f"Ответ: {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout при отправке в n8n")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка отправки в n8n: {e}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)

async def send_message_to_user(user_id, text):
    """
    Отправить сообщение пользователю (для ответов)
    Используется из n8n через HTTP запрос
    """
    try:
        await client.send_message(user_id, text)
        logger.info(f"✅ Сообщение отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки сообщения: {e}")

async def post_to_group(group_id, text):
    """
    Опубликовать сообщение в группу/канал
    """
    try:
        await client.send_message(group_id, text)
        logger.info(f"✅ Сообщение опубликовано в группу {group_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка публикации в группу: {e}")

async def main():
    """
    Основной цикл приложения
    """
    try:
        logger.info("🚀 Запуск Telegram Listener в Docker...")
        
        # Проверить переменные окружения
        if not all([API_ID, API_HASH, PHONE]):
            logger.error("❌ Не установлены обязательные переменные окружения")
            logger.error(f"API_ID: {bool(API_ID)}, API_HASH: {bool(API_HASH)}, PHONE: {bool(PHONE)}")
            sys.exit(1)
        
        # Запустить Flask в отдельном потоке для health check
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info("✅ Health check сервер запущен на порту 8000")
        
        # Подключиться к Telegram
        await client.start(phone=PHONE)
        logger.info("✅ Успешно подключено к Telegram")
        
        # Получить информацию о текущем аккаунте
        me = await client.get_me()
        logger.info(f"👤 Аккаунт: {me.first_name} (@{me.username})")
        logger.info(f"🔗 Webhook: {N8N_WEBHOOK}")
        
        # Слушать входящие сообщения
        logger.info("👂 Слушаю входящие сообщения...")
        await client.run_until_disconnected()
        
    except SessionPasswordNeededError:
        logger.error("❌ Требуется пароль 2FA")
        logger.error("Решение: 1) Отключить 2FA временно, или 2) Ввести пароль вручную")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("🔴 Telegram Listener остановлен")
        await client.disconnect()

if __name__ == '__main__':
    # Создать папки если их нет
    os.makedirs('/app/logs', exist_ok=True)
    os.makedirs('/app/sessions', exist_ok=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️  Остановлено пользователем")
