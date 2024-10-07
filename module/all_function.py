import configparser
import pickle
import random
import re
import os
import time
from datetime import datetime, timedelta

from tqdm import tqdm

from logs.logs import p_log
from setting import waiting_time, filename, mount_list


def remove_cyrillic(stroka: str):
    return re.sub(r'[а-яА-Я]', '', stroka).strip()  # 'Святлейший князь Rusty' -> 'Rusty'


def day(file):
    modification_time = os.path.getmtime(file)
    modification_date = datetime.fromtimestamp(modification_time)
    current_date = datetime.now()
    difference = current_date - modification_date
    difference_in_days = difference.days
    difference_in_hours = difference.seconds // 3600
    # Округление до ближайшего целого значения
    if difference_in_hours >= 12:
        difference_in_days += 1
    return difference_in_days


def wait_until(target_time_str):
    """Ожидание до указанного времени"""
    p_log(f"Ожидаем до {target_time_str}")
    target_time = datetime.strptime(target_time_str, "%H:%M").time()
    now = datetime.now()
    target_datetime = datetime.combine(now.date(), target_time)
    if now > target_datetime:
        # Если время уже прошло, запланируем на следующий день
        target_datetime += timedelta(days=1)
    sleep_duration = (target_datetime - now).total_seconds()
    return int(sleep_duration)


def get_config_value(key, default=0):
    config = configparser.ConfigParser()

    try:
        if not os.path.exists(filename):
            p_log(f"Error: The file '{filename}' does not exist.")
            return default

        config.read(filename)

        if 'DEFAULT' in config:
            if config.has_option('DEFAULT', key):
                val = config.get('DEFAULT', key)
                if val.isdigit():
                    return int(config.get('DEFAULT', key))
                return config.get('DEFAULT', key)
        return default

    except (configparser.Error, IOError) as e:
        p_log(f"Error: Failed to read the configuration file. {e}")
        return default


def save_file(data: dict, name_file: str):
    command = input().lower()
    if command == "y":
        with open(name_file, 'wb') as f:
            pickle.dump(data, f)
            print(f"Данные записаны в файл {name_file}")


day_list_1 = (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 25, 26, 27, 28, 29, 30)
day_list_2 = (2, 3, 4, 22, 23, 24)
day_list_3 = (1, 11, 21, 31)


def syntax_day(days_have_passed: int) -> str:
    if days_have_passed in day_list_1:
        return "дней"
    if days_have_passed in day_list_2:
        return "дня"
    else:
        return "день"


def create_folder(name):
    try:
        # Создаем папку
        os.makedirs(name)
        print(f"Папка '{name}' успешно создана.")
    except FileExistsError:
        # Если папка уже существует, пересоздаем её
        os.makedirs(name, exist_ok=True)
        print(f"Папка '{name}' уже существует, пересоздана.")


def current_time():
    return datetime.now().strftime("%H:%M:%S"), datetime.now()


def get_random_value():
    return random.uniform(0.1, 0.5)


def time_sleep(seconds=0):
    if seconds == 0:
        seconds = random.randint(waiting_time + 7, waiting_time + 20)
        for i in tqdm(range(seconds), desc="Ostalos vremeni", unit="sec"):
            time.sleep(1)
        p_log("Gotov k atake")
    else:
        for i in tqdm(range(seconds), desc="Ostalos vremeni", unit="sec"):
            time.sleep(1)


def format_time(seconds):
    """Форматирует время в строку формата '00:00:00'."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def time_sleep_main(total_seconds):
    interval = 10 * 60  # 10 минут в секундах
    remaining_time = total_seconds

    # Убедимся, что интервал не превышает общее время
    if interval > total_seconds:
        interval = total_seconds

    while remaining_time > 0:
        # Ожидание интервала времени
        time.sleep(min(interval, remaining_time))
        remaining_time -= min(interval, remaining_time)

        # Вывод информации о оставшемся времени
        # print(f"Осталось времени: {format_time(remaining_time)}")
        p_log(f"Процессу атаки осталось работать: {format_time(remaining_time)}")


def no_cache():
    return int(time.time() * 1000)


def get_name_mount(value):
    return next((k for k, v in mount_list.items() if v == value), value)
