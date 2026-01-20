#!/usr/bin/env python3
"""
Автоматическое извлечение API ID и Hash из my.telegram.org
Использует Selenium для автоматизации браузера
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys

def extract_api_credentials(phone):
    """
    Извлекает API ID и Hash из my.telegram.org
    
    Args:
        phone (str): Номер телефона в формате +79991234567
    
    Returns:
        dict: {'api_id': ..., 'api_hash': ...}
    """
    
    # Инициализируем браузер
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print(f"🌐 Открываем my.telegram.org...")
        driver.get("https://my.telegram.org/apps")
        
        # Ждем загрузки страницы
        time.sleep(3)
        
        # Вводим номер телефона
        print(f"📱 Вводим номер: {phone}")
        phone_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "sign_in_phone"))
        )
        phone_input.clear()
        phone_input.send_keys(phone)
        
        # Нажимаем кнопку "Next"
        next_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        next_button.click()
        
        print("⏳ Ожидаем кода подтверждения... (60 сек)")
        time.sleep(60)  # Даем время на ввод кода
        
        # После ввода кода ищем API ID и Hash
        print("🔍 Ищем API ID и Hash...")
        
        try:
            api_id = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "app_id"))
            ).text
            
            api_hash = driver.find_element(By.ID, "app_hash").text
            
            print(f"\n✅ УСПЕШНО!")
            print(f"API_ID: {api_id}")
            print(f"API_HASH: {api_hash}")
            
            # Сохраняем в .env
            env_content = f"""TELEGRAM_API_ID={api_id}
TELEGRAM_API_HASH={api_hash}
TELEGRAM_PHONE={phone}
"""
            
            with open('.env', 'w') as f:
                f.write(env_content)
            
            print(f"\n💾 Сохранено в .env")
            return {'api_id': api_id, 'api_hash': api_hash}
            
        except Exception as e:
            print(f"❌ Не удалось найти API данные: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None
    finally:
        driver.quit()

if __name__ == "__main__":
    phone = "+375259646826"  # ✏️ ИЗМЕНИТЕ НА ВАШУ!
    # Или: phone = sys.argv[1] if len(sys.argv) > 1 else "+375259646826"
    
    extract_api_credentials(phone)
