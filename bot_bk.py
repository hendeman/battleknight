import logging
import os
import requests
import telebot
import time
import threading
import re
from datetime import datetime

# Включаем логирование

telebot.logger.setLevel(logging.INFO)  # Уровни: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Настройка форматирования логов и их вывода в файл
logging.basicConfig(filename='telebot.log',
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    level=logging.INFO,  # Уровень логирования для основного логера
                    datefmt='%Y-%m-%d %H:%M:%S')
# Укажите здесь ваш токен и chat_id

TOKEN = '7577099222:AAHlMBv2kXRjjXQOxfp8SNNyBL14ZF7_rAs'
CHAT_ID = 808158849  # Ваш полученный chat_id
LOG_FILE = 'logs/app.log'  # Путь к вашему лог-файлу
# ALLOWED_USERS = {CHAT_ID}  # Множество разрешенных пользователей
log_time = 600
ALLOWED_USERS_FILE = 'allowed_users.txt'

bot = telebot.TeleBot(TOKEN)
is_running = False  # Флаг для контроля потока сообщений


def load_allowed_users():
    if os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, 'r') as f:
            users = {int(line.strip()) for line in f}  # Читаем id и преобразуем в целые числа
        users.add(CHAT_ID)  # Обеспечиваем, что ваш id всегда в списке
        return users
    return {CHAT_ID}  # Возвращаем множество с вашим id, если файла нет


def save_allowed_users():
    with open(ALLOWED_USERS_FILE, 'w') as f:
        for user_id in ALLOWED_USERS:
            f.write(f"{user_id}\n")  # Записываем каждое id в новую строку
    # Убедитесь, что ваш ID также сохраняется
    if CHAT_ID not in ALLOWED_USERS:
        ALLOWED_USERS.add(CHAT_ID)  # Добавляем ваш id, если его нет


ALLOWED_USERS = load_allowed_users()  # Загружаем пользователей из файла


# Функция для чтения последних 15 строк лог-файла
def read_last_lines(file, lines=15):
    with open(file, 'r') as f:
        # Читаем последние строки
        last_lines = f.readlines()[-lines:]

        # Объединяем строки в одну
    combined_lines = ''.join(last_lines)

    return combined_lines


# Команда /help — выводит описание доступных команд
@bot.message_handler(commands=['help'])
def send_help(message):
    if message.chat.id in ALLOWED_USERS:
        help_text = (
            "Доступные команды:\n"
            "/start - Показать последние 15 записей из лог-файла.\n"
            "/run - Показать последние 15 записей из лог-файла и продолжить отправлять новые записи.\n"
            "/stop - Остановить отправку новых записей лог-файла.\n"
            "/help - Показать это сообщение."
        )
        bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=['start'])
def add_me(message):
    chat_id = message.chat.id
    ALLOWED_USERS.add(chat_id)  # Добавляем chat_id в множество
    save_allowed_users()  # Сохраняем обновленный список
    bot.send_message(chat_id, f"Вы успешно добавлены. Ваш id={chat_id}")


@bot.message_handler(commands=['leave'])
def leave_me(message):
    chat_id = message.chat.id
    if chat_id in ALLOWED_USERS:
        ALLOWED_USERS.remove(chat_id)  # Удаляем chat_id из множества
        save_allowed_users()  # Сохраняем обновленный список
        bot.send_message(chat_id, "Вы были удалены из списка разрешенных пользователей.")
    else:
        bot.send_message(chat_id, "Вы не в списке разрешенных пользователей.")


@bot.message_handler(commands=['users'])
def list_users(message):
    if message.chat.id == CHAT_ID:
        users_list = "\n".join(map(str, ALLOWED_USERS))
        bot.send_message(CHAT_ID, f"Разрешенные пользователи:\n{users_list}")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для просмотра этого списка.")


# Команда /start — выводит последние 15 строк из лог-файла
@bot.message_handler(commands=['log'])
def send_last_logs(message):
    if message.chat.id == CHAT_ID:
        last_logs = read_last_lines(LOG_FILE)
        for user_id in ALLOWED_USERS:
            bot.send_message(user_id, f"Последние 15 записей лога:\n{last_logs}")


# Команда /run — выводит последние 15 строк и запускает поток для отправки новых сообщений
@bot.message_handler(commands=['run'])
def start_sending_logs(message):
    global is_running
    if message.chat.id not in ALLOWED_USERS:
        return  # Игнорировать команды от неразрешенных пользователей

    if is_running:
        bot.send_message(message.chat.id, "Логи уже отправляются в реальном времени!")
        return

    is_running = True

    def send_new_logs():
        last_position = 0

        while is_running:
            try:
                # Переоткрываем файл, если наступила полночь
                current_time = datetime.now()
                if current_time.hour == 0 and current_time.minute == 20:
                    last_position = 0

                with open(LOG_FILE, 'r') as f:
                    f.seek(last_position)
                    lines = f.readlines()
                    last_position = f.tell()  # Обновляем позицию

                    filtered_lines = []
                    capture_error = False

                    for line in lines:
                        if 'ERROR' in line:
                            filtered_lines.append(line)
                            capture_error = True
                        elif 'INFO' in line:
                            # Удаляем "INFO" из строки
                            filtered_lines.append(line.replace('INFO', '').strip())
                        elif 'DEBUG' in line:
                            continue  # Пропускаем DEBUG строки
                        elif capture_error:
                            # Если мы уже начали захватывать ошибку, продолжаем добавлять строки
                            if line.strip():  # Если строка не пустая, добавляем
                                filtered_lines.append(line)
                            # Останавливаем захват, если следующая строка — новая запись
                            else:
                                capture_error = False
                        else:
                            # Если мы не захватываем ошибку, продолжаем добавлять другие строки
                            filtered_lines.append(line)

                    processed_lines = [
                        re.sub(r'^\d{2}:\d{2}:\d{2}\s+\d*\s*', '', line).strip()
                        for line in filtered_lines
                    ]

                    if processed_lines:
                        try:
                            message = '\n'.join(processed_lines)
                            for user_id in ALLOWED_USERS:
                                try:
                                    bot.send_message(user_id, message)
                                except Exception as e:
                                    logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
                        except requests.exceptions.HTTPError as e:
                            if e.response.status_code == 502:
                                logging.error("Ошибка 502: Bad Gateway при отправке логов.")
                            else:
                                logging.error(f"HTTP ошибка: {e}.")
                            time.sleep(20)  # Задержка перед повторной попыткой

                    for _ in range(log_time):
                        time.sleep(1)  # Задержка 1 секунда
                        # Проверяем время каждые 1 секунду
                        current_time = datetime.now()
                        if current_time.hour == 0 and current_time.minute == 20:
                            last_position = 0
                            time.sleep(60)
                            break  # Прерываем задержку, чтобы выполнить новую проверку логов

            except FileNotFoundError:
                logging.error(f"Файл {LOG_FILE} не найден.")
                time.sleep(60)  # Подождем перед повторной проверкой

            except Exception as e:
                logging.error(f"Неизвестная ошибка при отправке логов: {e}.")
                time.sleep(5)  # Небольшая задержка перед повторной попыткой

    # Запускаем поток для отправки новых логов
    threading.Thread(target=send_new_logs, daemon=True).start()


# Команда /stop — останавливает поток отправки сообщений
@bot.message_handler(commands=['unrun'])
def stop_sending_logs(message):
    global is_running
    if message.chat.id == CHAT_ID:
        is_running = False
        bot.send_message(CHAT_ID, "Остановка отправки логов.")


# Запуск бота с обработкой возможных ошибок соединения
while True:
    try:
        bot.polling(none_stop=True)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 502:
            logging.error("Ошибка 502: Bad Gateway при получении обновлений от Telegram API.")
        else:
            logging.error(f"HTTP ошибка: {e}.")
        time.sleep(5)
    except Exception as e:
        logging.error(f"Неизвестная ошибка: {e}.")
        time.sleep(5)