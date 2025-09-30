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

is_running_run = False
is_running_wm = False
show_info = False  # Переменная для контроля вывода INFO сообщений
warning_list = []
# Словарь для хранения позиции для каждой команды
last_positions = {
    'run': 0,
    'wm': 0
}


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
                "/wm - Запуск отслеживания логов войны\n" 
                "/unrun - Остановка процесса отслеживания логов\n"
                "/unwm - Остановка процесса отслеживания war_логов\n"
                "/war - Вывести WARNING сообщения\n"
                "/ri - Включить вывод INFO\n"
                "/ris - Выключить вывод INFO\n"
                "/win - Вывести список атак\n"
                "/conf - Выводит config.ini\n"
                "/com -only=1 слив+атака\n"
                "/com -only=0 ничего не делаем\n"
                "/com -reduce=1 слив+атака\n"
                "/com -reduce=0 атака\n"
                "/com -online=1 слив+атака\n"
                "/com -online=0 слив"
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
            last_logs = read_last_lines(LOG_FILE_1)
            for user_id in ALLOWED_USERS:
                bot.send_message(user_id, f"Последние 15 записей лога:\n{last_logs}")

    @bot.message_handler(commands=['run'])
    def start_sending_logs(message):
        global is_running_run
        if message.chat.id not in ALLOWED_USERS:
            return  # Игнорировать команды от неразрешенных пользователей

        if is_running_run:
            bot.send_message(message.chat.id, "Логи для команды 'run' уже отправляются в реальном времени!")
            return

        is_running_run = True  # Устанавливаем флаг, что команда 'run' активна
        last_positions['run'] = 0  # Сбрасываем позицию для команды 'run'

        # Запускаем поток для отправки новых логов из первого файла
        threading.Thread(target=process_logs, args=(LOG_FILE_1, message, 'run', is_running_run), daemon=True).start()

    @bot.message_handler(commands=['wm'])
    def start_sending_wm_logs(message):
        global is_running_wm
        if message.chat.id not in ALLOWED_USERS:
            return  # Игнорировать команды от неразрешенных пользователей

        if is_running_wm:
            bot.send_message(message.chat.id, "Логи для команды 'wm' уже отправляются в реальном времени!")
            return

        is_running_wm = True  # Устанавливаем флаг, что команда 'wm' активна
        last_positions['wm'] = 0  # Сбрасываем позицию для команды 'wm'

        # Запускаем поток для отправки новых логов из второго файла
        threading.Thread(target=process_logs, args=(LOG_FILE_2, message, 'wm', is_running_wm), daemon=True).start()

    def process_logs(log_file, message, command, is_running):
        global warning_list

        while is_running:
            try:
                # Переоткрываем файл, если наступила полночь
                current_time = datetime.now()

                # Если наступило время для сброса last_position (например, в 7 утра)
                if current_time.hour == 0 and current_time.minute <= 10:
                    # Сбрасываем last_position только в случае команды "run"
                    if command == 'run':
                        last_positions[command] = 0
                    warning_list = []

                with open(log_file, 'r', encoding='utf-8') as f:
                    # Если нужно сбросить позицию, устанавливаем курсор в конец
                    if last_positions[command] == 0:
                        f.seek(0, 2)  # Устанавливаем в конец файла
                        last_positions[command] = f.tell()  # Обновляем позицию на конец файла
                    else:
                        f.seek(last_positions[command])  # Продолжаем с текущей позиции

                    lines = f.readlines()
                    last_positions[command] = f.tell()  # Обновляем позицию

                    filtered_lines = []
                    capture_error = False

                    for line in lines:
                        if 'ERROR' in line:
                            filtered_lines.append(line)
                            capture_error = True
                        elif 'INFO' in line and show_info:
                            filtered_lines.append(line.replace('INFO', '').strip())
                        elif 'INFO' in line:
                            continue
                        elif 'WARNING' in line:
                            warning_list.append(line.replace('WARNING', '').strip())
                        elif 'DEBUG' in line:
                            continue
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
                            log_message = '\n'.join(processed_lines) + war_mess
                            for user_id in ALLOWED_USERS:
                                max_length = 1000
                                parts = [log_message[i:i + max_length] for i in range(0, len(log_message), max_length)]
                                for part in parts:
                                    while True:  # Бесконечный цикл для повторных попыток
                                        try:
                                            bot.send_message(user_id, part)
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
                logging.error(f"Файл {log_file} не найден.")
                time.sleep(60)  # Подождем перед повторной проверкой

            except Exception as e:
                logging.error(f"Неизвестная ошибка при отправке логов: {e}.")
                time.sleep(5)  # Небольшая задержка перед повторной попыткой

    @bot.message_handler(commands=['unrun'])
    def stop_sending_logs(message):
        global is_running_run
        if message.chat.id in ALLOWED_USERS:  # Проверяем, что пользователь разрешен
            is_running_run = False  # Останавливаем отправку логов для 'run'
            last_positions['run'] = 0  # Сбрасываем позицию для команды 'run'
            bot.send_message(message.chat.id, "Остановка отправки логов для команды 'run'.")

    @bot.message_handler(commands=['unwm'])
    def stop_sending_wm_logs(message):
        global is_running_wm
        if message.chat.id in ALLOWED_USERS:  # Проверяем, что пользователь разрешен
            is_running_wm = False  # Останавливаем отправку логов для 'wm'
            last_positions['wm'] = 0  # Сбрасываем позицию для команды 'wm'
            bot.send_message(message.chat.id, "Остановка отправки логов для команды 'wm'.")

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
