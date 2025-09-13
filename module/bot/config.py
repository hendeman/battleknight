import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')
CHAT_ID = 808158849  # Ваш полученный chat_id
LOG_FILE_1 = 'logs/app/app.log'  # Путь к вашему лог-файлу
LOG_FILE_2 = 'logs/war/app.log'  # Путь к вашему лог-файлу
log_time = 20
ALLOWED_USERS_FILE = 'allowed_users.txt'
