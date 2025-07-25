import base64
import configparser
import json
import pickle
import random
import re
import os
import time
from datetime import datetime, timedelta

from tqdm import tqdm

from logs.logs import p_log
from setting import waiting_time, filename, mount_list, SAVE_CASTLE, GAME_TOKEN


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
    """
    :param key: название параметра из config.ini, либо несколько в виде key=("",)
    :param default:
    :return: когда параметр один, то возращает число, либо строку. Если несколько параметров, то возвращает словарь
    вида: {key(index): value, }
    """
    config = configparser.ConfigParser()

    # Проверяем, переданы ли несколько ключей (в виде tuple/list)
    is_multi_key = isinstance(key, (tuple, list))
    keys = key if is_multi_key else [key]

    try:
        if not os.path.exists(filename):
            print(f"Error: The file '{filename}' does not exist.")
            return {k: default for k in keys} if is_multi_key else default

        config.read(filename)

        if 'DEFAULT' not in config:
            return {k: default for k in keys} if is_multi_key else default

        # Обработка значений
        result = {}
        for k in keys:
            if config.has_option('DEFAULT', k):
                val = config.get('DEFAULT', k)
                # Проверяем, является ли значение int, float или строкой
                if val.isdigit():
                    result[k] = int(val)
                else:
                    try:
                        result[k] = float(val)  # Пробуем преобразовать в float
                    except ValueError:
                        result[k] = val  # Если не число, возвращаем строку
            else:
                result[k] = default

        # Возвращаем словарь (если ключей несколько) или одно значение
        return result if is_multi_key else result[key]

    except (configparser.Error, IOError) as e:
        print(f"Error: Failed to read the configuration file. {e}")
        return {k: default for k in keys} if is_multi_key else default


def change_config_value(section, key, new_value):
    config = configparser.ConfigParser()

    try:
        # Проверяем, существует ли файл
        if not os.path.exists(filename):
            p_log(f"Error: The file '{filename}' does not exist.", level='debug')
            return f"Файл '{filename}' не существует"

        config.read(filename)

        # Проверяем, существует ли ключ в секции
        if 'DEFAULT' in config and config.has_option(section, key) and new_value.isdigit():
            # Устанавливаем новое значение
            config.set(section, key, str(new_value))

            # Записываем изменения обратно в файл
            with open(filename, 'w') as configfile:
                config.write(configfile)

            p_log(f"Changed: [{section}] {key} = {new_value}", level='debug')
            return f"config.ini -> {key} установлено {new_value}"
        elif not new_value.isdigit():
            p_log(f"Error: value '{new_value}' not isdigit() '{section}'.", level='debug')
            return "Значение должно содержать только цифры"
        else:
            p_log(f"Error: Key '{key}' not found in section '{section}'.", level='debug')
            return "Неверное имя параметра"

    except (configparser.Error, IOError) as e:
        p_log(f"Error: Failed to write to the configuration file. {e}", is_error=True)
        return f"Error: Failed to read the configuration file. {e}"


def show_config():
    config = configparser.ConfigParser()
    output_lines = []  # Список для хранения строк конфигурации

    try:
        if not os.path.exists(filename):
            p_log(f"Error: The file '{filename}' does not exist.", level='debug')
            return f"Файл '{filename}' не существует"

        config.read(filename)

        # Добавляем содержимое каждой секции в список строк
        for section in config.sections():
            output_lines.append(f"[{section}]")
            for key, value in config.items(section):
                output_lines.append(f"{key} = {value}")
            output_lines.append("")  # Пустая строка для разделения секций

        # Если есть секция DEFAULT, выводим её содержимое
        if 'DEFAULT' in config:
            output_lines.append("[DEFAULT]")
            for key, value in config.items('DEFAULT'):
                output_lines.append(f"{key} = {value}")

        # Объединяем список строк в одну строку с разделителем "\n"
        return "\n".join(output_lines)

    except (configparser.Error, IOError) as e:
        p_log(f"Error: Failed to write to the configuration file. {e}", is_error=True)
        return f"Error: Failed to read the configuration file. {e}"


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


def get_random_value(a=0.1, b=0.5):
    return random.uniform(a, b)


def time_sleep(seconds=0):
    if seconds:
        for i in tqdm(range(int(seconds)), desc="Ostalos vremeni", unit="sec"):
            time.sleep(1)
    if seconds == 0:
        seconds = random.randint(waiting_time + 60, waiting_time + 120)
        for i in tqdm(range(seconds), desc="Ostalos vremeni", unit="sec"):
            time.sleep(1)
        p_log("Gotov k atake")


def format_time(seconds):
    """Форматирует время в строку формата '00:00:00'."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def time_sleep_main(total_seconds, interval=1800):
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
    return next((v['name'] for v in mount_list.values() if v['id_helper'] == str(value)), value)


def get_save_castle():
    try:
        with open(SAVE_CASTLE, 'rb') as file_gamer:
            p_log(f"Попытка открыть файл {SAVE_CASTLE}", level='debug')
            dict_gamer = pickle.load(file_gamer)
            if len(dict_gamer) > 1:
                p_log("В save_castle более одного ключа", is_error=True)
            return dict_gamer

    except FileNotFoundError:
        p_log("Файла не существует, будет создан новый", level='debug')
        dict_gamer = {}
        if get_config_value("fix_bad_keys"):
            p_log("Начальный город будет выбран Терент, чтобы открыть забагованные ключи", level='debug')
            dict_gamer['VillageOne'] = 'BanditLair'
        with open(SAVE_CASTLE, 'wb') as file_gamer:
            pickle.dump(dict_gamer, file_gamer)
        return dict_gamer


def clear_save_castle():
    with open(SAVE_CASTLE, 'wb') as file_gamer:
        dict_gamer = {}
        pickle.dump(dict_gamer, file_gamer)
        p_log(f"{SAVE_CASTLE} очищен", level='debug')


def write_save_castle(key, value):
    with open(SAVE_CASTLE, 'wb') as file_gamer:
        pickle.dump({key: value}, file_gamer)
        p_log(f"{SAVE_CASTLE} сохранились данные текущей миссии {key}:{value}", level='debug')


# ______________ Рекурсивно преобразует вложенные словари, чтобы они стали хешируемыми ______________
def dict_to_tuple(d):
    result = []
    for k in sorted(d.keys()):  # Сортируем ключи
        v = d[k]
        if isinstance(v, dict):
            v = dict_to_tuple(v)  # Рекурсивное преобразование
            result.append((k, v))
        else:
            result.append((k, v))
    return tuple(result)


def get_next_time_and_index(start_times):
    # Получаем текущее время
    now = datetime.now()

    # Переменная для хранения ближайшего времени и его индекса
    next_time = None
    next_index = -1

    for index, time_str in enumerate(start_times):
        # Преобразуем строку времени в объект datetime
        time_obj = datetime.strptime(time_str, '%H:%M').replace(year=now.year, month=now.month, day=now.day)

        # Если время уже прошло, добавляем один день
        if time_obj < now:
            time_obj += timedelta(days=1)

        # Находим ближайшее время
        if next_time is None or time_obj < next_time:
            next_time = time_obj
            next_index = index

    return next_index + 1, next_time.strftime('%H:%M')


def availability_id(user_id):
    decoded_bytes = base64.b64decode(GAME_TOKEN).decode('utf-8')
    p_log(f"decoded_bytes: {decoded_bytes}", level='debug')
    p_log(f"user_id: {user_id}", level='debug')
    return user_id == decoded_bytes


# _____________________ создание, загрузка и копия файла JSON __________________________________________

def save_json_file(dct: dict, path: str, name_file: str):
    path = path + name_file
    with open(path, "w", encoding="utf-8-sig") as f:
        json.dump(dct, f, ensure_ascii=False, indent=4)  # ensure_ascii=False для кириллицы
        p_log(f"Данные успешно сохранены в {path}")


def load_json_file(path: str, name_file: str) -> dict:
    path = path + name_file
    with open(path, "r", encoding="utf-8-sig") as f:
        loaded_data = json.load(f)
    return loaded_data


def backup_json_file(original_path: str, save_dir: str) -> str:
    """
    Создает копию JSON-файла с датой в имени.

    :param original_path: Путь к исходному JSON-файлу (например, 'data.json').
    :param save_dir: Директория для резервных копий (например, 'backups').
    :return: Путь к созданной копии.
    """
    # Проверяем, существует ли исходный файл
    if not os.path.exists(original_path):
        raise FileNotFoundError(f"Файл {original_path} не найден!")

    # Создаем директорию для резервных копий, если её нет
    os.makedirs(save_dir, exist_ok=True)

    # Получаем имя файла без расширения и его расширение
    file_name, ext = os.path.splitext(os.path.basename(original_path))

    # Форматируем текущую дату (например, '20_05_25' для 25 мая 2025 года)
    current_date = datetime.now().strftime("%y_%m_%d")

    # Формируем новое имя файла (например, 'data_20_05_25.json')
    backup_filename = f"{file_name}_{current_date}{ext}"
    backup_path = os.path.join(save_dir, backup_filename)

    # Копируем содержимое исходного файла в новый
    with open(original_path, 'r', encoding='utf-8-sig') as original_file:
        data = json.load(original_file)

    with open(backup_path, 'w', encoding='utf-8-sig') as backup_file:
        json.dump(data, backup_file, ensure_ascii=False, indent=4)

    p_log(f"Создана резервная копия: {backup_path}")
    return backup_path


# _________________________________________________________________________________________________

def check_file_exists(path_json_file: str, name_file: str) -> bool:
    """
    Проверяет, существует ли файл в указанной директории.

    :param path_json_file: Путь к директории (например, '/backups').
    :param name_file: Имя файла (по умолчанию 'data.json').
    :return: True если файл существует, иначе False.
    """
    full_path = os.path.join(path_json_file, name_file)
    return os.path.isfile(full_path)


def get_html_files(directory: str) -> list:
    """ Возвращает все html файлы в из директории directory """
    html_files = [entry.name for entry in os.scandir(directory) if entry.is_file() and entry.name.endswith('.html')]

    return html_files
