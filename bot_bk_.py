import logging
import telebot
import time
import requests
from module.bot.config import TOKEN
from module.bot.logger import setup_logging
from module.bot.handlers import register_handlers

setup_logging()
bot = telebot.TeleBot(TOKEN)
register_handlers(bot)

# Основной цикл
while True:
    try:
        bot.polling()
    except requests.exceptions.ReadTimeout:
        logging.error("Ошибка соединения с Telegram API. Повторная попытка через 300 секунд...")
        time.sleep(300)  # Ждем 60 секунд перед повторной попыткой

    except requests.exceptions.ConnectionError:
        logging.error("Проблема с интернет-соединением. Повторная попытка через 300 секунд...")
        time.sleep(300)  # Ждем 60 секунд перед повторной попыткой

    except Exception as e:
        logging.error(f"Неизвестная ошибка: {e}. Повторная попытка через 300 секунд...")
        time.sleep(300)  # Ждем 60 секунд перед повторной попыткой