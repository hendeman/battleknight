import pickle
import re
import threading
import time
from datetime import datetime
import requests
import logging

from module.all_function import change_config_value, show_config
from module.bot.config import *
from module.bot.utils import load_allowed_users, save_allowed_users, read_last_lines

ALLOWED_USERS = load_allowed_users(ALLOWED_USERS_FILE, CHAT_ID)

is_running = False
show_info = False  # Переменная для контроля вывода INFO сообщений
last_position = 0  # Глобальная переменная для хранения позиции
warning_list = []


def register_handlers(bot):
    @bot.message_handler(commands=['help'])
    def send_help(message):
        if message.chat.id in ALLOWED_USERS:
            help_text = (
                "Доступные команды:\n"
                "/users - Разрешенные пользователи\n"
                "/leave - Перестать получать сообщения\n"
                "/log - Показать последние 15 записей из лог-файла.\n"
                "/run - Запуск отслеживания логов\n"   
                "/unrun - Остановка процесса отслеживания логов\n"
                "/war - Вывести WARNING сообщения\n"
                "/ri - Включить вывод INFO\n"
                "/ris - Выключить вывод INFO\n"
                "/win - Вывести список атак\n"
                "/conf - Выводит config.ini\n"
                "/com -online=1 слив+атака\n"
                "/com -online=0 ничего не делаем\n"
                "/com -reduce=1 слив+атака\n"
                "/com -reduce=0 атака\n"
                "/com -only=1 слив+атака\n"
                "/com -only=0 слив"
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
        global is_running, last_position
        if message.chat.id not in ALLOWED_USERS:
            return  # Игнорировать команды от неразрешенных пользователей

        if is_running:
            bot.send_message(message.chat.id, "Логи уже отправляются в реальном времени!")
            return

        is_running = True
        last_position = 0  # Сбрасываем позицию при запуске

        def send_new_logs():
            global last_position, warning_list  # Используем global для изменения глобальной переменной

            while is_running:
                try:
                    # Переоткрываем файл, если наступила полночь
                    current_time = datetime.now()
                    if current_time.hour == 7 and current_time.minute <= 10:
                        last_position = 0
                        warning_list = []

                    with open(LOG_FILE, 'r', encoding='utf-8') as f:
                        # Устанавливаем курсор в конец файла при первом запуске
                        if last_position == 0:
                            f.seek(0, 2)  # Устанавливаем в конец файла
                            last_position = f.tell()  # Обновляем позицию на конец файла
                        else:
                            f.seek(last_position)

                        lines = f.readlines()
                        last_position = f.tell()  # Обновляем позицию

                        filtered_lines = []
                        capture_error = False

                        for line in lines:
                            if 'ERROR' in line:
                                filtered_lines.append(line)
                                capture_error = True
                            elif 'INFO' in line and show_info:  # Проверяем переменную show_info
                                filtered_lines.append(line.replace('INFO', '').strip())
                            elif 'INFO' in line:
                                continue
                            elif 'WARNING' in line:
                                warning_list.append(line.replace('WARNING', '').strip())
                            elif 'DEBUG' in line:
                                continue  # Пропускаем DEBUG строки
                            elif capture_error:
                                if line.strip():  # Если строка не пустая, добавляем
                                    filtered_lines.append(line)
                                else:
                                    capture_error = False
                            else:
                                filtered_lines.append(line)

                        processed_lines = [
                            re.sub(r'^\d{2}:\d{2}:\d{2}\s+\d*\s*', '', line).strip()
                            for line in filtered_lines
                        ]

                        if processed_lines:
                            try:
                                war_mess = f"\nwarning {len(warning_list) * '*'}" if warning_list else ""
                                message = '\n'.join(processed_lines) + war_mess
                                for user_id in ALLOWED_USERS:
                                    while True:  # Бесконечный цикл для повторных попыток
                                        try:
                                            bot.send_message(user_id, message)
                                            break  # Выход из цикла при успешной отправке
                                        except requests.exceptions.ConnectionError as e:
                                            logging.error(
                                                f"Ошибка соединения при отправке сообщения пользователю {user_id}: {e}")
                                            time.sleep(10)  # Задержка 10 секунд перед повторной попыткой
                            except requests.exceptions.HTTPError as e:
                                if e.response.status_code == 502:
                                    logging.error("Ошибка 502: Bad Gateway при отправке логов.")
                                else:
                                    logging.error(f"HTTP ошибка: {e}.")
                                time.sleep(20)  # Задержка перед повторной попыткой

                    time.sleep(600)

                except FileNotFoundError:
                    logging.error(f"Файл {LOG_FILE} не найден.")
                    time.sleep(60)  # Подождем перед повторной проверкой

                except Exception as e:
                    logging.error(f"Неизвестная ошибка при отправке логов: {e}.")
                    time.sleep(5)  # Небольшая задержка перед повторной попыткой

        # Запускаем поток для отправки новых логов
        threading.Thread(target=send_new_logs, daemon=True).start()

    @bot.message_handler(commands=['unrun'])
    def stop_sending_logs(message):
        global is_running, last_position
        if message.chat.id in ALLOWED_USERS:  # Проверяем, что пользователь разрешен
            is_running = False
            last_position = 0  # Сбрасываем позицию при остановке
            bot.send_message(message.chat.id, "Остановка отправки логов.")

    @bot.message_handler(commands=['win'])
    def send_last_logs(message):
        if message.chat.id == CHAT_ID:
            for user_id in ALLOWED_USERS:
                with open('pickles_data/gamer_gold.pickle', 'rb') as game_file:
                    loaded_dict = pickle.load(game_file)
                    current_time = datetime.now().date()
                    dct = {v['name']: (v['win_status'], v['spoil']) for k, v in loaded_dict.items()
                           if v['win_status'] and v['time'].date() == current_time}
                    if not dct:
                        bot.send_message(user_id, f"Вражеский список атак пуст")
                    else:
                        result = []
                        for name, (action, amount) in dct.items():
                            if 'lupatik' in action:
                                result.append(f"{action} {name}, получено {amount} серебра")
                            else:
                                result.append(f"{action}, отдано {amount} серебра")

                        st = "\n".join(result)
                        bot.send_message(user_id, st)

    @bot.message_handler(commands=['ri'])
    def enable_info_logs(message):
        global show_info
        show_info = True
        bot.send_message(message.chat.id, "INFO сообщения теперь включены в вывод.")

    @bot.message_handler(commands=['ris'])
    def disable_info_logs(message):
        global show_info
        show_info = False
        bot.send_message(message.chat.id, "INFO сообщения теперь отключены от вывода.")

    @bot.message_handler(commands=['war'])
    def send_last_logs(message):
        if message.chat.id == CHAT_ID:
            for user_id in ALLOWED_USERS:
                if warning_list:
                    st = "\n".join(warning_list)
                    bot.send_message(user_id, st)
                else:
                    bot.send_message(user_id, 'WARNING ошибок не обнаружено')

    @bot.message_handler(commands=['com'])
    def handle_ris(message):
        if message.chat.id == CHAT_ID:
            for user_id in ALLOWED_USERS:
                # Получаем текст сообщения, убирая команду /ris
                command_text = message.text[len('/com '):].strip()

                # Разделяем текст по пробелам
                params = command_text.split()

                # Словарь для хранения параметров
                options = {}

                for param in params:
                    if param.startswith('-'):
                        # Разделяем параметр на ключ и значение
                        key_value = param[1:].split('=')
                        if len(key_value) == 2:
                            key = key_value[0].strip()
                            value = key_value[1].strip()
                            options[key] = value

                # Обработка параметров
                if 'reduce' in options:
                    mess = change_config_value('DEFAULT', 'reduce_experience', options['reduce'])
                    bot.send_message(user_id, mess)
                elif 'only' in options:
                    mess = change_config_value('DEFAULT', 'online_tracking_only', options['only'])
                    bot.send_message(user_id, mess)
                elif 'online' in options:
                    mess = change_config_value('DEFAULT', 'online_track', options['online'])
                    bot.send_message(user_id, mess)
                else:
                    bot.send_message(user_id, "Неверный параметр")

    @bot.message_handler(commands=['conf'])
    def handle_ris(message):
        if message.chat.id == CHAT_ID:
            for user_id in ALLOWED_USERS:
                bot.send_message(user_id, show_config())
