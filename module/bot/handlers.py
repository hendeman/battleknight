import re
import threading
import time
from datetime import datetime
import requests
import logging
from module.bot.config import *
from module.bot.utils import load_allowed_users, save_allowed_users, read_last_lines

ALLOWED_USERS = load_allowed_users(ALLOWED_USERS_FILE, CHAT_ID)

is_running = False


def register_handlers(bot):
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
        ALLOWED_USERS.add(chat_id)
        save_allowed_users(ALLOWED_USERS_FILE, ALLOWED_USERS)
        bot.send_message(chat_id, f"Вы успешно добавлены. Ваш id={chat_id}")

    @bot.message_handler(commands=['leave'])
    def leave_me(message):
        chat_id = message.chat.id
        if chat_id in ALLOWED_USERS:
            ALLOWED_USERS.remove(chat_id)
            save_allowed_users(ALLOWED_USERS_FILE, ALLOWED_USERS)
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

                    with open(LOG_FILE, 'r', encoding='utf-8') as f:
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
