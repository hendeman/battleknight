import base64
import binascii
import configparser
import json
import pickle
import random
import re
import os
import sys
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Optional, Any
from inspect import signature

import psutil
from tqdm import tqdm

from logs.logs import p_log
from setting import waiting_time, SAVE_CASTLE, get_filename, NICKS_GAMER, GOLD_GAMER, attack_ids_path, \
    LOG_ERROR_HTML, get_name, SERVER, reload_cookies

# Глобальный кэш
_config_cache: Optional[configparser.ConfigParser] = None
_config_mtime = 0
_config_filename = None
date = datetime(2024, 9, 17, 19)


def check_last_word(url):
    """ Функция проверки последнего слова в url на наличие заглавной буквы"""
    url = url.rstrip('/')
    last_word = url.split('/')[-1]

    for char in last_word:
        if char.isupper():
            return True
    return False


def remove_cyrillic(bad_string: str):
    return re.sub(r'[а-яА-Я]', '', bad_string).strip()  # 'Святлейший князь Rusty' -> 'Rusty'


def get_prefix_url(url=SERVER):
    match = re.search(r'-(.*?)\.', url)  # Ищем текст между '-' и первой следующей '.'
    if match:
        result = match.group(1)
        p_log(f"Получен префикс {result}", level="debug")
        return result
    raise ValueError(f"Не удалось найти префикс в строке: {url}")


def digi(bad_string: str) -> int:
    return int(re.findall(r'\b\d+\b', bad_string)[0])  # 'element.addClass('activity0'+6)' -> 6


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


def string_to_datetime(date_string):
    """

    :param date_string: '2025-10-23 16:34:51'
    :return: date_time_obj
    """
    try:
        return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        p_log(f"Неверный формат даты {date_string}", level='warning')
        return None
    except TypeError:
        return None


def get_config_value(key, default=0):
    """
    Оптимизированная версия с кэшированием config
    """
    global _config_cache, _config_mtime, _config_filename

    # Получаем актуальное имя файла
    current_filename = get_filename()

    # Если файл изменился или это первый вызов
    if (_config_cache is None or
            _config_filename != current_filename or
            _should_reload_config(current_filename)):
        _load_config_cache(current_filename)

    # Проверяем, переданы ли несколько ключей
    is_multi_key = isinstance(key, (tuple, list))
    keys = key if is_multi_key else [key]

    # Обработка значений из кэша
    result = {}
    for k in keys:
        if _config_cache.has_option('DEFAULT', k):
            val = _config_cache.get('DEFAULT', k)
            # Преобразование типов
            if val.isdigit():
                result[k] = int(val)
            else:
                try:
                    result[k] = float(val)
                except ValueError:
                    result[k] = val
        else:
            result[k] = default

    return result if is_multi_key else result[key]


def _should_reload_config(filename):
    """Проверяет, нужно ли обновить кэш"""
    global _config_mtime

    if not os.path.exists(filename):
        return True

    try:
        current_mtime = os.path.getmtime(filename)
        return current_mtime > _config_mtime
    except OSError:
        return True


def _load_config_cache(filename):
    """Загружает config в кэш"""
    global _config_cache, _config_mtime, _config_filename

    config = configparser.ConfigParser()

    try:
        if os.path.exists(filename):
            config.read(filename)
            _config_mtime = os.path.getmtime(filename)
        else:
            print(f"Warning: Config file '{filename}' does not exist. Using empty config.")
            config['DEFAULT'] = {}

    except (configparser.Error, IOError) as e:
        print(f"Error reading config: {e}")
        config['DEFAULT'] = {}  # Пустой config

    _config_cache = config
    _config_filename = filename


def change_config_value(section, key, new_value):
    filename = get_filename()
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
    filename = get_filename()
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


def save_file(data: dict, name_file: str, auto_save: bool = False):
    """
    Сохраняет данные в файл.

    Args:
        data: Данные для сохранения
        name_file: Имя файла
        auto_save: Если True, сохраняет без запроса подтверждения
    """
    if auto_save:
        # Автоматическое сохранение без запроса
        with open(name_file, 'wb') as f:
            pickle.dump(data, f)
            p_log(f"Данные автоматически записаны в файл {name_file}")
    else:
        # Сохранение с запросом подтверждения
        command = input("Сохранить файл? (y/n): ").lower()
        if command == "y":
            with open(name_file, 'wb') as f:
                pickle.dump(data, f)
                p_log(f"Данные записаны в файл {name_file}")
        else:
            p_log("Сохранение отменено")


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


def time_sleep(seconds=0, delay=False):
    # Если seconds is False, функция ничего не делает
    if seconds is None:
        return

    # Определяем время ожидания
    if seconds == 0:
        wait_time = random.randint(waiting_time + 60, waiting_time + 120)
    elif delay:
        wait_time = random.randint(seconds + 60, seconds + 120)
    else:
        wait_time = int(seconds)  # Приводим к int, на случай если передали float

    # Логируем и выполняем ожидание, только если wait_time > 0
    if wait_time > 0:
        if delay or seconds == 0:
            p_log(f"Ожидание {wait_time} сек перед следующей атакой...")

        for i in tqdm(range(int(wait_time)),
                      desc="Waiting",
                      unit="sec",
                      file=sys.stdout,
                      dynamic_ncols=True,
                      position=0,
                      leave=False,
                      delay=1):
            time.sleep(1)

        if delay or seconds == 0:
            p_log("Готов к атаке")
    # Если wait_time <= 0, просто выходим без ожидания


def format_time(seconds):
    """
    Форматирует время в строку формата 'Xд Xч Xм Xс'.
    Показывает только ненулевые значения.

    Args:
        seconds: Время в секундах

    Returns:
        Отформатированная строка времени
    """
    seconds = int(seconds)

    # Разбиваем на составляющие
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Формируем части только для ненулевых значений
    parts = []
    if days > 0:
        parts.append(f"{days} d")
    if hours > 0:
        parts.append(f"{hours} h")
    if minutes > 0:
        parts.append(f"{minutes} min")
    if seconds > 0 or not parts:  # Если все нули, показываем хотя бы секунды
        parts.append(f"{seconds} sec")

    return f"<{', '.join(parts)}>"


def time_sleep_main(total_seconds, interval=1800, name="Осталось"):
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
        p_log(f"{name}: {format_time(remaining_time)}")


def no_cache():
    return int(time.time() * 1000)


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


def availability_id(user_id, not_token=False):
    if not_token:
        p_log(f"user_id: {user_id}", level='debug')
        return not_token

    p_log(f"user_id: {user_id}", level='debug')
    token_list = str(get_config_value("access_granted")).split(',')

    for token in token_list:
        try:
            decoded_bytes = base64.b64decode(token.strip()).decode('utf-8')
            p_log(f"decoded_bytes: {decoded_bytes}", level='debug')
            if user_id == decoded_bytes:
                return True

        except (UnicodeDecodeError, binascii.Error) as er:
            p_log(f'Error decode access_granted={token.strip()}: {er}', level='debug')
            continue

    return False


# _____________________ создание, загрузка и копия файла JSON __________________________________________

def save_json_file(dct: dict, path: str, name_file: str):
    file_path = os.path.join(path, name_file)
    normalized_path = os.path.normpath(file_path)
    with open(file_path, "w", encoding="utf-8-sig") as f:
        json.dump(dct, f, ensure_ascii=False, indent=4)  # ensure_ascii=False для кириллицы
        p_log(f"Данные успешно сохранены в {normalized_path}")


def load_json_file(path: str, name_file: str) -> dict:
    file_path = os.path.join(path, name_file)
    with open(file_path, "r", encoding="utf-8-sig") as f:
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


def check_name_companion(dct, item_find: str):
    """

    :param dct:"companion": [
        {
            "item_id": "15517097",
            "item_fullName": "Кролик",
            "item_pic": "Companion06",
            "speed_travel": 0,
            "item_use": 0,
            "type_helper": "компаньон",
            "number_bag": 6
        }]...
    :param item_find: "Companion06"
    :return: {элемент словаря, в котором есть item_find}.
    """
    for helper, data_helper in dct.items():
        if not data_helper:
            continue
        for item in data_helper:
            if item.get('item_pic') == item_find:
                return item


def get_name_companion(dct, id_find: int):
    """
    :param id_find:
    :param dct:"companion": [
        {
            "item_id": "15517097",
            "item_fullName": "Кролик",
            "item_pic": "Companion06",
            "speed_travel": 0,
            "item_use": 0,
            "type_helper": "компаньон",
            "number_bag": 6
        }]....
    :param id_find: 16896645
    :return: "Черный Боевой Медведь"
    """
    for helper, data_helper in dct.items():
        if not data_helper:
            continue
        for item in data_helper:
            if item.get('item_id') == str(id_find):
                return item.get('item_fullName')


def all_party(a: dict, b: dict) -> dict:
    all_dct_new = {}
    for x, y in zip(a.items(), b.items()):
        y[1]["time"] = x[1]
        all_dct_new.setdefault(x[0], y[1])
    return all_dct_new


# _____________________________ Создание, чтение, изменение pickle ____________________________________________
def read_conf_txt(loaded_dict):
    try:
        with open(attack_ids_path, 'r', encoding='utf-8-sig') as file_nicks:
            for i in file_nicks:
                id_gold = i.replace("\n", "").replace(" ", "").split(":")
                key = id_gold[0]
                gold = 0 if len(id_gold) == 1 else id_gold[1]
                if key not in loaded_dict:
                    loaded_dict[key] = {"time": date, "spoil": int(gold)}
    except FileNotFoundError:
        p_log(f"Файл {attack_ids_path} не найден")
    except Exception as e:
        p_log(f"Ошибка чтения {attack_ids_path}: {e}")

    return loaded_dict


def create_pickle_file(name_file=GOLD_GAMER, loaded_dict: dict = None):
    if loaded_dict is None:
        loaded_dict = read_conf_txt({})

    with open(name_file, 'wb') as f:
        pickle.dump(loaded_dict, f)
        p_log(f"Данные успешно обновлены в файл {name_file}. Всего {len(loaded_dict)} записей")


def change_pickle_file(name_file=NICKS_GAMER, loaded_dict: dict = None):
    if not os.path.exists(name_file):
        with open(name_file, 'wb') as f:
            pickle.dump({}, f)

    with open(name_file, 'rb+') as f:
        if loaded_dict is None:
            loaded_dict = read_conf_txt(pickle.load(f))
        f.seek(0)  # Перемещение курсора в начало файла
        f.truncate()  # Очистка содержимого файла
        pickle.dump(loaded_dict, f)
        p_log(f"Данные успешно обновлены в файл {name_file}. Всего {len(loaded_dict)} записей")


def read_pickle_file(name_file=NICKS_GAMER):
    try:
        with open(f"{name_file}", 'rb') as f:
            loaded_dict = pickle.load(f)
            p_log(f"Всего {len(loaded_dict)} записей")
            for key, value in loaded_dict.items():
                p_log(f'{key}:{value}')
    except FileNotFoundError:
        p_log(f"Файл {name_file} не найден")
    except ValueError as er:
        p_log(f"Нарушена структура файла {name_file}. Ошибка: {er}")


def conv_pickle_txt_id(path_pickle: str, path_txt: str) -> None:
    """
    Функция для пересохранения pickle -> txt
    :param path_pickle: путь для pickle файла
    :param path_txt: путь для txt файла
    :return: None
    """
    try:
        with open(f"{path_pickle}", 'rb') as f:
            loaded_dict = pickle.load(f)
        with open(path_txt, 'w', encoding='utf-8-sig') as f:
            f.write('\n'.join(str(key) for key in loaded_dict))
        p_log(f"ID успешно сохранены в {path_txt}. Всего {len(loaded_dict)}")
    except FileNotFoundError:
        p_log(f"Файл {path_pickle} не найден")


def update_pickle_field(filename: str, field_name: str, new_value: Any) -> None:
    """
    Обновляет указанное поле во всех записях.

    Args:
        filename: Путь к файлу
        field_name: Имя поля для обновления
        new_value: Новое значение
    """
    with open(filename, 'rb') as f:
        data = pickle.load(f)

    updated_count = 0
    for key, value in data.items():
        if isinstance(value, dict) and field_name in value:
            value[field_name] = new_value
            updated_count += 1

    with open(filename, 'wb') as f:
        pickle.dump(data, f)

    p_log(f"Поле '{field_name}' обновлено в {updated_count} записях", level='debug')


def find_files_with_word(directory: Path, find_word: str) -> Path:
    """
    Найти файлы, содержащие слово в имени
    :param directory:  Директория для поиска файла
    :param find_word:  Слово, которое содержит файл
    :return: Полный пусть к файлу
    """

    for filename in os.listdir(directory):
        if find_word.lower() in filename.lower():
            return directory / filename
    p_log(f"В директории {directory} нет файлов с именем {find_word}", level='debug')
    return directory / find_word


# __________________________________________ Декоратор ленивой загрузки параметров ______________________________
def call_parameters(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        sig = signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        # Обрабатываем каждый параметр
        for param_name in bound.arguments:
            param_value = bound.arguments[param_name]

            # Если параметр callable и его нужно выполнить
            if callable(param_value):
                result = param_value()

                # Заменяем callable на результат выполнения
                bound.arguments[param_name] = result

        # Вызываем с обновленными аргументами
        return func(*bound.args, **bound.kwargs)

    return wrapper


def save_error_html(response):
    try:
        os.makedirs(LOG_ERROR_HTML, exist_ok=True)
        to_day = date.today()

        # Базовое имя файла с временной меткой
        base_filename = (f"{get_name()}_{to_day.day:02d}_{to_day.month:02d}_{to_day.hour:02d}_"
                         f"{to_day.minute:02d}_{to_day.second:02d}")

        # 1. Сохраняем полное тело ответа в бинарном виде
        body_filepath = os.path.join(LOG_ERROR_HTML, f"{base_filename}.html")
        content_length = len(response.content)
        with open(body_filepath, 'wb') as file_html:
            file_html.write(response.text)

            # 2. Сохраняем мета-информацию и превью для анализа
            meta_filepath = os.path.join(LOG_ERROR_HTML, f"{base_filename}_meta.txt")

            with open(meta_filepath, 'w', encoding='utf-8') as file:
                file.write("=" * 60 + "\n")
                file.write("ДИАГНОСТИКА ОТВЕТА СЕРВЕРА\n")
                file.write("=" * 60 + "\n\n")

                # Основная информация
                file.write("📋 ОСНОВНАЯ ИНФОРМАЦИЯ:\n")
                file.write(f"URL: {response.url}\n")
                file.write(f"Status code: {response.status_code}\n")
                file.write(f"Reason: {response.reason}\n")
                file.write(f"Elapsed time: {response.elapsed.total_seconds()} сек\n")
                file.write("\n")

                # Информация о кодировке
                file.write("🔤 КОДИРОВКА:\n")
                file.write(f"resp.encoding: {response.encoding}\n")
                file.write(f"resp.apparent_encoding: {response.apparent_encoding}\n")
                file.write(
                    f"resp.headers.get('Content-Type'): {response.headers.get('Content-Type', 'Not specified')}\n")
                file.write("\n")

                # Размер ответа
                file.write("📊 РАЗМЕР ОТВЕТА:\n")
                file.write(f"Длина resp.content: {content_length} байт ({content_length / 1024:.2f} КБ)\n")

                if content_length == 0:
                    file.write("⚠️ ВНИМАНИЕ: Ответ пустой (0 байт)!\n")
                file.write("\n")

                # Все заголовки ответа
                file.write("📌 ЗАГОЛОВКИ ОТВЕТА:\n")
                for key, value in response.headers.items():
                    file.write(f"{key}: {value}\n")
                file.write("\n")

                # Превью первых байт ответа (как сырые байты)
                file.write("🔍 ПРЕВЬЮ ОТВЕТА (первые 500 байт):\n")
                file.write("-" * 40 + "\n")

                preview_bytes = response.content[:500]

                # Сохраняем в двух представлениях: как текст и как hex
                file.write("\n📝 Как текст (если возможно раскодировать):\n")
                try:
                    # Пробуем раскодировать с разными кодировками
                    for enc in [response.encoding, response.apparent_encoding, 'utf-8', 'windows-1251', 'koi8-r',
                                'latin1']:
                        if enc:
                            try:
                                preview_text = preview_bytes.decode(enc)
                                file.write(f"  Кодировка {enc}: {repr(preview_text)}\n")
                            except (UnicodeDecodeError, TypeError):
                                continue
                except Exception as e:
                    file.write(f"  Ошибка декодирования: {e}\n")

                file.write("\n🔢 Как hex-дамп (байты):\n")
                # Форматируем hex дамп
                hex_lines = []
                for i in range(0, len(preview_bytes), 16):
                    chunk = preview_bytes[i:i + 16]
                    hex_part = ' '.join(f'{b:02x}' for b in chunk)
                    ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                    hex_lines.append(f"  {i:04x}: {hex_part:<48} {ascii_part}")

                file.write('\n'.join(hex_lines))

                if len(response.content) > 500:
                    file.write(f"\n\n  ... и еще {len(response.content) - 500} байт")

                file.write("\n\n" + "=" * 60 + "\n")
                file.write(f"Полное тело ответа сохранено в: {body_filepath}\n")
        p_log(f"HTML-ошибка сохранена в: {body_filepath}", level='debug')
    except Exception as er:
        p_log(f"Error saving HTML file in {LOG_ERROR_HTML}. Error: {er}", level='debug')


# __________________________ Функция для завершения процесса со всеми вложенными процессами ___________________
def kill_process_hierarchy(pid):
    """Убивает процесс и всю его иерархию потомков"""
    try:
        processes = psutil.Process(pid)

        # Получаем всех потомков (рекурсивно)
        children = processes.children(recursive=True)
        p_log(f"Найдено потомков: {len(children)}", level='debug')

        # Сначала убиваем всех потомков
        for child in children:
            try:
                p_log(f"Завершаем потомка: {child.pid}", level='debug')
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        children = processes.children(recursive=True)
        p_log(f"Обновление потомков. Найдено: {len(children)}", level='debug')
        # Ждем завершения потомков
        if children:
            gone, alive = psutil.wait_procs(children, timeout=2)
            for child in alive:
                try:
                    p_log(f"Принудительно убиваем: {child.pid}", level='debug')
                    child.kill()
                except psutil.NoSuchProcess:
                    pass

        # Затем убиваем родительский процесс
        p_log(f"Завершаем родительский процесс: {processes.pid}", level='debug')
        processes.terminate()
        processes.wait(timeout=2)

    except psutil.NoSuchProcess:
        p_log(f"Процесс {pid} не найден", level='warning')


def reload_setting_param(values: dict):
    """
    Функция для копирования изменяемых значений основного процесса setting в дочерний:
    (ENV_NAME, NAME, filename, LOG_DIR_NAME)
    :param values: словарь значений
    :return:
    """
    import setting

    # Специальная обработка для env_file
    if values.get('env_file') != setting.ENV_NAME:
        reload_cookies(values.get('env_file'))

    # Обновление остальных параметров
    updates = [
        ('name', 'NAME'),
        ('config', 'filename'),
        ('log_profile', 'LOG_DIR_NAME')
    ]

    for key, attr_name in updates:
        if key in values:
            new_value = values[key]
            current_value = getattr(setting, attr_name)
            if new_value != current_value:
                setattr(setting, attr_name, new_value)
