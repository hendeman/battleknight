import ast
import json
import os
import pickle
import re
import threading
from typing import Union, Tuple
from time import sleep
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from requests import Response

from logs.logs import p_log
from module.all_function import time_sleep, wait_until, no_cache, dict_to_tuple, get_random_value, \
    get_config_value, save_json_file, load_json_file, check_name_companion, get_name_companion, format_time, \
    current_time
from module.data_pars import heals, get_status_helper, pars_healer_result, get_all_silver, pars_gold_duel, \
    check_cooldown_poit, set_name, get_id, find_item_data, get_karma_value
from module.http_requests import post_request, make_request
from setting import *

date = datetime(2024, 9, 17, 19)


def print_status(from_town, where_town, how, tt):
    p_log(
        f"{'Едем' if how == 'horse' else 'Плывем'} "
        f"из {castles_all[from_town]} в {castles_all[where_town]}. "
        f"Ожидание {tt}"
    )


def check_timer():
    response = make_request(mission_url)
    soup = BeautifulSoup(response.text, 'lxml')
    response = soup.find('h1').text.strip()
    if response in status_list:
        time_sleep(check_progressbar())


def seconds_to_hhmmss(seconds):
    if seconds is None:
        return None
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"


def convert_to_minutes(time_str):
    """ Value time_str 01h 20m convert in int(minutes)"""
    time_pattern = re.compile(r'(\d{1,2})h\s*(\d{1,2})m')
    match = time_pattern.match(time_str)

    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        total_minutes = hours * 60 + minutes
        return total_minutes
    else:
        raise ValueError("Invalid time format")


# _________________________________ Найти ближайший замок с аукционами ________________________________

def get_castle_min_time():
    soup = BeautifulSoup(make_request(url_world).text, 'lxml')

    # Словарь для хранения результатов
    travel_times = {}
    st_pattern = re.compile(r"startTravel\('([a-zA-Z]+)', 'horse', new Element\(this\), false\);")

    # Поиск всех <tr> тегов
    for tr in soup.find_all('tr'):
        # Поиск <a> тега с onclick атрибутом
        a_tag = tr.find('a', class_='button boxed tooltip')
        if a_tag and 'onclick' in a_tag.attrs:
            onclick_value = a_tag['onclick']

            # Применение регулярного выражения
            travel_match = st_pattern.search(onclick_value)
            if travel_match:
                travel_name = travel_match.group(1)  # Извлекаем значение 'GhostTown'

                # Поиск времени в <td class="travelTable03 toolTip">
                time_td = tr.find('td', class_='travelTable03 toolTip')
                if time_td:
                    travel_time = time_td.get_text(strip=True)  # Убираем лишние пробелы
                    travel_time_minutes = convert_to_minutes(travel_time)
                    travel_times[travel_name] = travel_time_minutes
    p_log(travel_times, level='debug')
    filtered_dct = {key: value for key, value in travel_times.items() if key in auction_castles}
    castle_min_range = min(filtered_dct, key=filtered_dct.get)
    # Вывод результата
    p_log(filtered_dct, level='debug')
    p_log(f'Ближайший замок с аукционами в {castles_all.get(castle_min_range)}')
    return castle_min_range


def go_auction(out, going_back=True, tariff_travel=0):
    try:
        castle_auction = get_castle_min_time()
        post_travel(out=out, where=castle_auction)
        buy_ring(tariff_travel=tariff_travel)
        if going_back:
            post_travel(out=castle_auction, where=out)
    except Exception as er:
        p_log(f'Ошибка выполнения функции go_auction: {er}', level='warning')


# _____________________ Проверка состояния check_progressbar, проверка на работу progressbar_ends
def check_progressbar(resp=None):
    if resp is None:
        resp = make_request(mission_url)
    # heals(resp)
    soup = BeautifulSoup(resp.text, 'lxml')
    element = soup.find('h1').text.strip()
    p_log("Проверка состояния")

    if element in status_list:
        p_log(f"{get_name()} status <{element}>")
        return progressbar_ends(soup)
    p_log(f"{get_name()} свободен")


def progressbar_ends(soup):
    try:
        timer = soup.find(id="progressbarEnds").text.strip()
        hours, minutes, seconds = map(int, timer.split(':'))
        total_seconds = hours * 3600 + minutes * 60 + seconds + 2
    except AttributeError:
        if soup.find('h1').text.strip() == 'Работа':
            get_reward()
        total_seconds = 0

    return total_seconds


# __________ Использовать зелье use_potion, получить данные о зельях_________________________

def check_health(heals_point=False):
    resp = make_request(duel_url)
    life_count = heals(resp)
    if life_count < 10:
        if heals_point:

            # проверка на перезарядку зелья
            try:
                p_log('Проверка на перезарядку зелья')
                cooldown_timer = check_cooldown_poit(resp)
                if cooldown_timer:
                    p_log(f"Нельзя использовать зелье. Перезарядка {cooldown_timer} секунд")
                    time_sleep(cooldown_timer)
            except Exception as er:
                p_log(f"Ошибка получения значения перезарядки зелья: {er}", level='warning')
                time_sleep(600)

            use_potion()
            resp = make_request(duel_url)
            return heals(resp)
        else:
            p_log("Отдыхаем 10 минут, пока не восстановится здоровье")
            time_sleep()
            resp = make_request(duel_url)
            return heals(resp)
    return life_count


def use_potion():
    try:
        last_item_id, last_item_value = get_potion_bar()
        p_log(f"Будет использовано зелье на {last_item_value} HP")
        sleep(get_random_value())
        use_url = (
            f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/usePotion?noCache={no_cache()}&id={last_item_id}'
            '&merchant=false&table=user')
        make_request(use_url)
        sleep(get_random_value())
        # Получить новый список зелья
        get_potion_bar()
    except Exception as err:
        p_log(f"Ошибка в получении банок ХП. Отдыхаем 10 минут. Ошибка: {err}", level='warning')
        time_sleep(600)


def get_potion_bar():
    payload = {
        'noCache': f'{int(time.time() * 1000)}'
    }
    data = post_request(point_url, payload).json()
    result = ', '.join(f"{item['item_pic']} - {str(item['count'])}" for item in data)
    p_log(result)
    last_item_id, last_item_value = data[-1]['item_id'], data[-1]['item_value']
    return last_item_id, last_item_value


# ________________________ Проверить казну _____________________________________________

def check_treasury_timers():
    soup = BeautifulSoup(make_request(treasury_url).text, 'lxml')
    element = soup.find(class_='scrollLongTall')

    # Проверяем наличие класса hidden. Если есть hidden, то доступна казна
    if element and 'hidden' not in element.get('class', []):
        p_log(f"Казна не доступна, подождите': {element.text.strip().split()[0]}")
        return progressbar_ends(soup)


# ____________________________ Скинуть золото в казну ____________________________________
def contribute_to_treasury():
    gold_all = put_gold(status="before")
    payload = {'silvertoDeposit': int(gold_all * CURRENT_TAX) - 100}
    p_log(payload, level='debug')
    post_request(deposit_url, payload)
    return put_gold(status="after")


def put_gold(status="before"):
    soup = BeautifulSoup(make_request(treasury_url).text, 'lxml')
    gold_count_element = int(soup.find(id="silverCount").text.split()[0])
    p_log(
        f"Количество золота на руках: {gold_count_element}" if status == "before"
        else f"Осталось золота после казны: {gold_count_element}")
    return gold_count_element


def use_helper(config_name, restore=True, direct_call=False):
    """Декоратор для использования наездника/компаньона.

        Args:
            config_name (str): Параметр наездника/компаньона из config.ini (например, comp_tournament, comp_fight...).
            restore (bool): Вернуть исходного наездника/компаньона после выполнения (по умолчанию True).
            direct_call (bool): Если True, декоратор выполнится сразу без привязки к функции.
        """

    def use_companion_deco(func):
        def wrapper(*args, **kwargs):
            name_companion = get_config_value(config_name)
            available_helpers = {}
            validate_helper = None
            try:
                available_helpers = load_json_file("", url_helper_json)
                validate_helper = check_name_companion(available_helpers, name_companion)
            except Exception as er:
                p_log(f'Ошибка получения помощника {er}', level='warning')
            if validate_helper:
                id_helper_start = None
                id_helper = validate_helper.get('item_id')
                type_helper = validate_helper.get('type_helper')
                num_inventory = validate_helper.get('number_bag')
                url_helper = (f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/getInventory/?noCache={no_cache()}'
                              f'&inventory={num_inventory}&loc=character')
                response = make_request(user_url)
                make_request(url_helper)
                helper = get_status_helper(response, type_helper)
                if helper and helper != id_helper:
                    id_helper_start = helper
                if not id_helper_start and helper != id_helper:
                    p_log("Никакой помощник не надет")
                    id_helper_start = (
                        check_name_companion(available_helpers, get_config_value('horse_tournament')).get('item_id')
                        if type_helper == type_helper_name[0]
                        else check_name_companion(available_helpers, get_config_value('comp_tournament')).get('item_id')
                    )

                if helper != id_helper:
                    resp = make_request(
                        f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/wearItem/?noCache={no_cache()}"
                        f"&id={id_helper}&type=normal&invID={num_inventory}&loc=character")
                    if resp.json()['result']:
                        name_helper = get_name_companion(available_helpers, resp.json()['data']['id'])
                        p_log(f"{type_helper} {name_helper} надет")

                if not direct_call:
                    func(*args, **kwargs)

                if restore and get_config_value("ignor_mount"):
                    resp = make_request(
                        f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/wearItem/?noCache={no_cache()}"
                        f"&id={id_helper_start}&type=normal&invID={num_inventory}&loc=character")
                    if resp.json()['result']:
                        name_helper = get_name_companion(available_helpers, resp.json()['data']['id'])
                        p_log(f"{type_helper} {name_helper} надет")
            else:
                p_log(f"{name_companion} не найден в списке mount_list", level='debug')
                if not direct_call:
                    func(*args, **kwargs)

        return wrapper

    if direct_call:
        return use_companion_deco(lambda: None)()  # Автоматически вызываем

    return use_companion_deco


@use_helper("horse_travel")
def post_travel(out='', where='', how='horse'):
    payload = {
        'travelwhere': f'{where}',
        'travelhow': f'{how}',
        'travelpremium': 0
    }
    p_log(payload, level='debug')
    make_request(url_world)
    resp = post_request(travel_url, payload)
    timer_travel = check_progressbar(resp)
    if not timer_travel:
        p_log("Рыцарь не уехал в другой город!", level='warning', is_error=True)
    else:
        print_status(out, where, how, seconds_to_hhmmss(timer_travel))
        time_sleep(timer_travel)


# __________________________________ Рождественский ивент ________________________________________
def christmas_bonus(func=None):
    if func is None:
        return lambda f: christmas_bonus(f)

    def wrapper(*args, **kwargs):
        p_log("Проверка рюкзака добычи на еду")
        bonus_items = get_item_loot('christmas')
        if bonus_items:
            bonus_item = random.choice(bonus_items)
            p_log("Попытка применить рожденственский баф на миссию")
            url_bonus = (f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/'
                         f'activateQuestItem/{bonus_item}/lootbag?noCache={no_cache()}')
            try:
                resp = make_request(url_bonus).json()
                p_log(resp, level='debug')
                if resp['result']:
                    p_log('Баф активирован')
                else:
                    p_log(f"Баф не был активирован: {resp['reason']}, {resp['data']}", level='warning')
            except Exception as er:
                p_log(f"Ошибка обработки запроса рожденственского бонуса: {er}", level='warning')
            get_item_loot('christmas')
        else:
            p_log("Еды в рюкзаке добычи не обнаружено")
        func(*args, **kwargs)

    return wrapper


def apply_christmas_bonus(func):
    if CHRISTMAS_MODE:
        return christmas_bonus(func)
    return func


# ________________________________________________________________________________________________


@apply_christmas_bonus
def post_dragon(name_mission, buy_rubies='', sleeping=True):
    payload = {
        'chooseMission': name_mission,
        'missionArt': get_config_value("mission_duration"),
        'missionKarma': get_config_value("working_karma"),
        'buyRubies': buy_rubies
    }

    resp = post_request(post_url, payload)
    p_log(f"С миссии <{name_mission}> получено {pars_gold_duel(resp, gold_info=True)} серебра")
    if buy_rubies:
        p_log(f"Потрачен {buy_rubies} рубин")
    p_log(f"Всего {get_all_silver(resp)} серебра")
    if sleeping:
        time_sleep()


def check_hit_point():
    while True:
        response = make_request(map_url)
        if heals(response) < 20:
            p_log("Отдыхаем 10 минут, пока не восстановится здоровье")
            time_sleep(610)
        else:
            break


def my_place():
    response = make_request(mission_url)
    soup = BeautifulSoup(response.text, 'lxml')
    place = soup.find('h1').text.strip()
    for key, value in castles_all.items():
        if value == place:
            return value, key
    return place, None


def is_time_between(start_hour: str, end_hour: str):
    now = datetime.now().time()
    start_tm = datetime.strptime(start_hour, "%H:%M").time()
    end_tm = datetime.strptime(end_hour, "%H:%M").time()
    return start_tm <= now <= end_tm


def check_time_sleep(start_hour: str, end_hour: str, sleep_hour: str = None):
    # Получаем текущее время
    now = datetime.now().time()

    # Преобразуем строки в объекты time
    start_tm = datetime.strptime(start_hour, "%H:%M").time()
    end_tm = datetime.strptime(end_hour, "%H:%M").time()

    # Проверяем, находится ли текущее время в заданном диапазоне
    if end_tm < start_tm:
        # Если интервал переходит через полночь
        in_range = now >= start_tm or now <= end_tm
    else:
        # Обычный интервал в пределах одного дня
        in_range = start_tm <= now <= end_tm

    if in_range and sleep_hour:
        time_sleep(wait_until(sleep_hour))
    if in_range and sleep_hour is None:
        return True


def hide_silver(silver_limit):
    soup = BeautifulSoup(make_request(world_url).text, 'lxml')
    silver_count = int(soup.find(id='silverCount').text)
    if silver_count > silver_limit and check_treasury_timers() is None:
        return contribute_to_treasury()
    return silver_count


def get_silver(resp: Union[bool, Response] = False):
    if isinstance(resp, Response):
        soup = BeautifulSoup(resp.text, 'lxml')
    else:
        soup = BeautifulSoup(make_request(world_url).text, 'lxml')
    silver_count = int(soup.find(id='silverCount').text)
    p_log(f"На руках {silver_count} серебра")
    return silver_count


def get_gold_for_player(gamer) -> int:
    url_gamer = f'https://s32-ru.battleknight.gameforge.com/common/profile/{gamer}/Scores/Player'
    resp = make_request(url_gamer)
    time.sleep(0.5)
    soup = BeautifulSoup(resp.text, 'lxml')
    gold = int(soup.find('table', class_='profileTable').find_all('tr')[3].text.split()[2])
    return gold


def check_status_mission(name_mission):
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    length_mission = get_config_value("mission_duration")
    karma_mission = get_config_value("working_karma")
    st = f"chooseMission('{length_mission}', '{name_mission}', '{karma_mission}', this)"
    a_tags = soup.find_all('a', onclick=lambda onclick: onclick and st in onclick)
    return a_tags


def get_all_items(item, num_inv: Union[int, Tuple[int, int]] = None):
    dct_inventory = {
        "key": r'^Clue\d+_closed$',
        "points": r'PotionRed\d+'
    }

    pattern = re.compile(dct_inventory[item])
    item_key_list = {}

    # Определяем диапазон инвентарей
    if isinstance(num_inv, tuple) and len(num_inv) == 2:
        inventories = range(num_inv[0], num_inv[1] + 1)
    elif isinstance(num_inv, int):
        inventories = [num_inv]
    else:
        inventories = range(1, 5)  # По умолчанию, если num_inv не задан

    for i in inventories:
        url = (f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/getInventory/?noCache={no_cache()}'
               f'&inventory={i}&loc=character')
        resp = make_request(url)

        try:
            if resp.json()['result']:
                for item_data in resp.json()['items']:
                    if pattern.match(item_data['item_pic']):
                        if item == "key":
                            item_key_list[item_data['item_id']] = {
                                'item_pic': item_data['item_pic'],
                                'location': item_data['clue_data']['location']
                            }
                        else:
                            item_key_list[item_data['item_id']] = item_data['item_pic']
        except ValueError:
            p_log("Ошибка ставки. Ошибка json(). Неверный запрос получения инвентаря", level='warning')

        sleep(1)  # Задержка между запросами

    p_log(f"Словарь с {item} успешно сформирован", level='debug')
    return item_key_list


def check_mission(name_mission, buy_rubies=''):
    check_hit_point()  # проверка количества здоровья
    dct1 = get_group_castles(get_all_items("key"))
    p_log(dct1, level='debug')
    post_dragon(
        length_mission=get_config_value("mission_duration"),
        name_mission=name_mission,
        karma_mission=get_config_value("working_karma"),
        buy_rubies=buy_rubies
    )
    make_request(mission_url)  # Запрос в миссии для обновления ключей
    dct2 = get_group_castles(get_all_items("key"))
    p_log(dct2, level='debug')
    differences = set(dict_to_tuple(dct1)) ^ set(dict_to_tuple(dct2))
    p_log(differences, level='debug')
    return differences


def get_group_castles(dct: dict):
    grouped_data = {}
    for item_id, attributes in dct.items():
        location = attributes['location']
        item_pic = attributes['item_pic']

        if location not in grouped_data:
            grouped_data[location] = {'count': 0, 'item_pic': {}}

        grouped_data[location]['count'] += 1
        grouped_data[location]['item_pic'][item_id] = item_pic
    return grouped_data


# __________________ Купить зелье мудрости за 800 серебра ________________
def post_healer(potion_number):
    payload = {'potion': f'potion{str(potion_number)}'}
    name_potion = event_healer_potions[potion_number]['name']
    p_log(f"Запрос на покупку <{name_potion}>")
    resp = post_request(healer_url, payload)
    try:
        dct = resp.json()
        p_log(dct, level='debug')
        description_html = dct.get('description', '')
        pars_healer_result(description_html)
    except Exception as er:
        p_log(f'Ошибка json покупки <{name_potion}>: {er}', level='debug')


def do_matrix_inventory(data, size):
    rows = size['width']
    cols = size['depth']
    matrix = [data[i * rows:(i + 1) * rows] for i in range(cols)]
    return matrix


# __________________ Получаем случайное значение номера сумки и координаты свободного слота __________________

def choose_random_coor(dct, rand):
    if dct:
        if rand:
            random_key = random.choice(list(dct.keys()))
            random_value = random.choice(dct[random_key])
            result = {random_key: random_value}
            return result
        else:
            # Находим максимальный ключ
            max_key = max(dct.keys(), key=int)

            # Находим максимальный кортеж для этого ключа
            max_tuple = min(dct[max_key], default=None)

            # Формируем итоговый словарь
            result = {max_key: max_tuple}
            return result
    else:
        p_log("Нет свободных слотов в сумке")


# _______________________ Получаем данные заполненности инвентаря в 3 и 4 сумке _______________________________

def get_inventory_slots(num_inv):
    # Определяем диапазон инвентарей
    try:
        inventories = ast.literal_eval(num_inv)
    except ValueError:
        if isinstance(num_inv, int):
            inventories = [num_inv]
        else:
            inventories = range(1, 5)

    item_key_list = {}
    for i in inventories:
        url_inventory = (f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/getInventory/?noCache={no_cache()}'
                         f'&inventory={i}&loc=character')
        resp = make_request(url_inventory)

        try:
            result = resp.json()
            if resp.json()['result'] and result['inventory']:
                item_key_list[f"{i}"] = do_matrix_inventory(result['inventory'], result['inventorySize'])
        except ValueError:
            p_log("Ошибка ставки. Ошибка json(). Неверный запрос получения инвентаря", level='warning')
        except KeyError as er:
            p_log(f"Нет доступных ключей, ошибка {er}", level='warning')
        sleep(1)
    return item_key_list


# ________________________________ Преобразование данных инвентаря в матричный вид _________________

def get_free_coord(original_dict):
    coordinates_dict = {}

    # Преобразование
    for key, matrix in original_dict.items():
        coordinates = []  # Список для хранения координат
        for row_index, row in enumerate(matrix):
            for col_index, value in enumerate(row):
                if value == '0':  # Если значение равно '0'
                    coordinates.append((row_index, col_index))  # Добавляем кортеж (строка, столбец)
        if coordinates:
            coordinates_dict[key] = coordinates  # Записываем в новый словарь
    p_log(coordinates_dict, level='debug')
    return coordinates_dict


# _____________________________ Проверить, если ли общий ключ в продаже ____________________________________

def get_item_market():
    soup = BeautifulSoup(make_request(url_market).text, 'lxml')
    items_market = soup.find(id='merchItemLayer')
    small_key = items_market.find('div', class_='itemClue01_closed')
    element_id = small_key['id'] if small_key and 'id' in small_key.attrs else None
    if element_id:
        id_key = ''.join(filter(lambda x: x.isdigit(), element_id))
        p_log(f"В продаже имеется общий ключ {id_key}")
        return [id_key]
    p_log('Нет ключей в продаже')


def get_item_loot(item_name):
    dct_loot = {"ring": r'itemRing\d+',
                "key": r'itemClue\d+_closed',
                "christmas": ['itemFastingPeriodSalt', 'itemFastingPeriodBread', 'itemFastingPeriodNuts']}
    soup = BeautifulSoup(make_request(url_loot).text, 'lxml')
    items_loot = soup.find(id='lootContent')
    item_list = []
    if item_name in dct_loot:
        # Если значение — это строка (регулярное выражение)
        if isinstance(dct_loot[item_name], str):
            pattern = re.compile(dct_loot[item_name])
            for item in items_loot.find_all('div'):
                if pattern.search(' '.join(item.get('class', []))):
                    id_key = ''.join(filter(lambda x: x.isdigit(), item['id']))
                    item_list.append(id_key)
        # Если значение — это список
        elif isinstance(dct_loot[item_name], list):
            for sub_item in dct_loot[item_name]:
                pattern = re.compile(sub_item)
                for item in items_loot.find_all('div'):
                    if pattern.search(' '.join(item.get('class', []))):
                        id_key = ''.join(filter(lambda x: x.isdigit(), item['id']))
                        item_list.append(id_key)
    if item_list:
        p_log(f"Доступные {item_name} в сундуке добычи: {item_list}")
        return item_list
    p_log(f"В сундуке добычи нет {item_name}")


# ____________________________ Основная функция покупки ключа на рынке ____________________________________

def move_item(how='buy', name='key', rand=True):
    id_key = get_item_loot(name) if how == 'loot' else get_item_market()
    if id_key:
        for item in id_key:
            inventory = get_inventory_slots(get_config_value(key='searching_slots_bag'))
            free_coord = get_free_coord(inventory)
            dct_coor = choose_random_coor(free_coord, rand)
            if dct_coor:
                inv, coor = next(iter(dct_coor.items()))
                p_log(f"Попытка переместить {name} {item} в сумку {inv}, ячейка {coor}")
                if how == 'buy':
                    url_buy_item = (
                        f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/buyItem/?noCache={no_cache()}&id={item}'
                        f'&inventory={inv}&width={coor[1]}&depth={coor[0]}')
                    make_request(url_buy_item)
                elif how == 'loot':
                    url_loot_item = (
                        f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/placeItem/?noCache={no_cache()}&id={item}'
                        f'&inventory={inv}&width={coor[1]}&depth={coor[0]}&type=tmp')
                    make_request(url_loot_item)
            else:
                break
            sleep(2)


# _______________________ Покупка кольца на аукционе за все серебро _____________________________

def place_bet(id_item, bet):
    payload = {'noCache': no_cache()}
    resp = post_request(f'https://s32-ru.battleknight.gameforge.com/ajax/market/bid/{id_item}/{bet}', payload)
    try:
        if resp.json()['result']:
            p_log("Ставка выполнена успешно")
        else:
            p_log(f"Ошибка ставки, неверное количество серебра")
    except ValueError:
        p_log("Ошибка ставки. Ошибка json(). Неверный id_item", level='warning')


def payout(silver_out: int):
    to_silver = get_silver()
    payload = {'silverToPayout': silver_out}
    post_request(url_payout, payload)
    after_silver = get_silver()
    if after_silver - to_silver == silver_out:
        p_log(f"Из казны взято {silver_out} серебра")
        return after_silver
    else:
        p_log(f"Ошибка запроса взять из казны to_silver={to_silver}, after_silver={after_silver}")


def handle_ring_operations(a: int, b: bool):
    """
    Обрабатывает операции с кольцом: обновление цены после 13:00 и покупку
    """
    cost_ring_auction = a
    counter_reset_ring_auction = b

    def wrapper(silver):
        nonlocal cost_ring_auction, counter_reset_ring_auction
        p_log(f"cost_ring_auction={cost_ring_auction}, "
              f"counter_reset_ring_auction={counter_reset_ring_auction}", level='debug')
        if is_time_between(start_hour='13:00', end_hour='15:00') and not counter_reset_ring_auction:
            cost_ring_auction = buy_ring(initial=True)
            counter_reset_ring_auction = True

        # Установка значения по умолчанию, если cost_ring_auction равен None
        cost_ring_auction = cost_ring_auction or 0

        conditions = [cost_ring_auction,
                      silver > cost_ring_auction - 500,
                      not is_time_between(start_hour='11:00', end_hour='13:00')
                      ]

        if all(conditions) and get_config_value("buy_ring"):
            buy_ring()  # покупка кольца на аукционе
            cost_ring_auction = buy_ring(initial=True)

    return wrapper


def buy_ring(initial=False, tariff_travel=0):
    response = make_request(url_auctioneer)
    soup = BeautifulSoup(response.text, 'lxml')
    auction_item_box = soup.find_all('div', class_='auctionItemBox')
    # проверить "auctionItemBox" когда аукционер ничего не представил
    # print(len(auction_item_box))
    dct = {}
    for item in auction_item_box:
        # Находим нужный div с классом itemRing
        item_ring_div = item.find('div', class_=lambda x: x and x.startswith('itemRing'))
        if item_ring_div:
            # Извлекаем id
            id_item = item_ring_div['id'][8:]  # Обрезаем 'auctItem' для получения цифр

            # Находим input с нужным id
            bid_text_input = soup.find('input', id=f'bidText{id_item}')

            # Извлекаем значение value
            if bid_text_input:
                bid_value = bid_text_input['value']
                dct[id_item] = bid_value
    target_number = get_silver() - tariff_travel
    p_log(f"Доступно {target_number} серебра")
    p_log(dct, level='debug')

    if not dct:
        p_log("Нет колец на аукционе")
    else:
        min_key = min(dct, key=lambda k: int(dct[k]))
        min_value = int(dct[min_key])
        if initial:
            return min_value

        if min_value > target_number:
            need_silver = min_value - target_number
            p_log(f"Недостаточно серебра для ставки. Нужно еще {need_silver}")
            if need_silver < 500:
                after_silver = payout(need_silver)
                place_bet(min_key, after_silver)
        else:
            p_log(f"Будет куплено кольцо с id={min_key}")
            place_bet(min_key, target_number)


# ________________________ Регистрация на турнире _____________________________________

def register_joust():
    now = datetime.now()
    month_number = now.day
    if month_number % 3 == 0:
        try:
            resp = make_request(url_joust)
            soup = BeautifulSoup(resp.content, 'lxml')
            try:
                joust = soup.find(id="btnApply").text
            except AttributeError:
                joust = "Не найден"
            silver = int(soup.find(id="silverCount").text)
            if joust == "Регистрация":
                contribution = int(soup.find('div', class_='formField').text)
                if silver < contribution:
                    payout(contribution - silver)
                resp = make_request(url_joust_sign).json()
                p_log(resp, level='debug')
                p_log("Вы зарегистрированы на турнир")
            else:
                p_log("Вы уже участвуете в турнире")
        except Exception as err:
            p_log(f"Ошибка регистрации на турнир: {err}", level='warning')


# __________________________________ Покупка баночек HP до нужного количества _______________________________

def main_buy_potion(count_points):
    all_points = len(get_all_items("points", 1))  # получение количества баночек в сумке 1
    if all_points < count_points:
        buy_potion(count_points - all_points)  # покупка необходимого количесва баночек HP
    else:
        p_log("В сумке достаточное количество баночек здоровья")


def buy_potion(need_point):
    while need_point:
        resp = make_request(url_alchemist)
        soup = BeautifulSoup(resp.text, 'lxml')
        silver = int(soup.find(id='silverCount').text)
        items_loot = soup.find(id='merchItemLayer').find_all('div')
        potion_dct = {}
        for item in items_loot:
            merch_item = item.get('id', None)
            item_potion = set(potion_name_buy).intersection(set(item.get('class', None)))
            if merch_item and item_potion:
                merch_id = ''.join(re.findall(r'\d+', merch_item))
                potion_dct[merch_id] = list(item_potion)[0]
        if potion_dct:
            p_log(f"В продаже есть {potion_dct}")
            min_key = min(potion_dct, key=lambda k: conv_name_potion(potion_dct[k]))
            min_value = conv_name_potion(potion_dct[min_key])
            p_log(min_key)
            if silver > min_value * 2:
                # Получение свободных ячеек в 1 инвентаре
                inventory = get_inventory_slots(1)
                free_coord = get_free_coord(inventory)
                free_coord_one = choose_coor(free_coord)
                inv, coor = next(iter(free_coord_one.items()))
                p_log(f"Попытка купить баночку на {min_value}ХП в сумку {inv}, ячейка {coor}")
                url_potion_buy = (
                    f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/buyItem/?noCache={no_cache()}&id={min_key}'
                    f'&inventory={inv}&width={coor[1]}&depth={coor[0]}')
                make_request(url_potion_buy)
                need_point -= 1
            else:
                p_log("Недостаточно серебра для покупки баночек HP")
                break
        else:
            p_log("В продаже нет доступных баночек HP")
            break


def choose_coor(dct):
    if dct:
        # Находим минимальную свободную сумку
        max_key = min(dct.keys(), key=int)

        # Находим максимальное значение координат
        max_tuple = max(dct[max_key], default=None)

        # Формируем итоговый словарь
        result = {max_key: max_tuple}
        return result
    else:
        p_log("Нет свободных слотов в сумке")


def conv_name_potion(potion):
    potion_value = int(''.join(re.findall(r'\d+', potion)))
    return potion_value


# ____________Отправить рыцаря на работу work и получить награду за работу get_reward___________
@use_helper("comp_work")
def work(working_hours, side='good'):
    payload = {
        'hours': working_hours,
        'side': side
    }
    make_request(work_url)
    time.sleep(1)
    post_request(work_url, payload)
    p_log(f"Работаем {working_hours} часов...")


def get_reward():
    make_request(work_url)
    payload = {'paycheck': 'encash'}

    post_request(work_url, payload)
    p_log(f"Награда за работу принята")


# _________________________________ Обновление данных активности игроков файла battle.json __________

def init_status_players():
    try:
        with open(url_name_json, 'r', encoding='utf-8') as file:
            list_of_players = json.load(file)
            for player, values in list_of_players.items():
                current_loot = get_gold_for_player(player)
                loot_per_day = current_loot - values.get('loot', 0)
                if loot_per_day > values.get('gold_diff'):
                    p_log(f"Игрок {values.get('name')} активен. Добыча {loot_per_day}")
                    if values.get('initiative'):
                        list_of_players[player]['allow_attack'] = True
                    else:
                        list_of_players[player]['allow_attack'] = False
                else:
                    p_log(f"Игрок {values.get('name')} не активен")
                    list_of_players[player]['allow_attack'] = False

                list_of_players[player]['loot_per_day'] = loot_per_day
                list_of_players[player]['loot'] = current_loot

        with open(url_name_json, 'w') as file_gamer:
            json.dump(list_of_players, file_gamer, indent=4)
            p_log(f"Файл {url_name_json} обновлен", level='debug')

    except json.decoder.JSONDecodeError as er:
        print(f"Ошибка в структуре файла {url_name_json}: {er}")


# _____________________________ Получение компаньонов и наездников __________________________


def get_use_helper():
    response = make_request(user_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    dct = {}

    for helper, data_helper in NAME_HELPERS.items():
        item_horse = soup.find(id=data_helper.get('item_name')).find('div',
                                                                     {'id': lambda x: x and x.startswith('item')})
        item_id = item_horse['id'].replace('item', '') if item_horse else None

        item_data = find_item_data(soup, item_id)
        if item_data:  # Если данные не None
            item_data['type_helper'] = data_helper.get('type_helper_names')
            number_bag = BAG_CONFIG.get(helper)
            item_data['number_bag'] = number_bag if isinstance(number_bag, int) else number_bag[0]
            dct.setdefault(helper, []).append(item_data)
        else:  # Если None — создаём пустой список
            dct.setdefault(helper, [])

    return dct


def get_helper_bag(bag_num=None):
    def data_parsing(helper_type, num_bag, dct):
        url_helper = (f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/getInventory/?noCache={no_cache()}'
                      f'&inventory={num_bag}&loc=character')
        resp = make_request(url_helper)
        resp_json = resp.json()
        if not resp_json.get('result'):
            return
        helpers = resp_json.get('items', [])
        if not helpers:
            dct.setdefault(helper_type, [])
            return dct
        for item in helpers:
            item_data = {
                'item_id': item.get('item_id'),
                'item_fullName': item.get('item_fullName'),
                'item_pic': item.get('item_pic'),
                'speed_travel': item.get('item_special_ability').get('HorseTravelTimeReduction', 0)
                if item.get('item_special_ability')
                else 0,
                'item_use': int(item.get('item_use', 0)),
                'type_helper': NAME_HELPERS[helper_type].get('type_helper_names'),
                'number_bag': num_bag
            }
            dct.setdefault(helper_type, []).append(item_data)
        return dct

    result = {}
    if bag_num is None:
        for helper, nums in BAG_CONFIG.items():
            bag_numbers = [nums] if isinstance(nums, int) else nums
            for num in bag_numbers:
                result = data_parsing(helper, num, result)
    else:
        if bag_num not in ALL_BAG_NUMS:
            raise ValueError(f"Не существует сумки с номером {bag_num}")
        helper = next(
            (key for key, value in BAG_CONFIG.items()
             if value == bag_num or (isinstance(value, tuple) and bag_num in value)),
            None
        )

        result = data_parsing(helper, bag_num, result)

    return result


def all_helper(save_json=True):
    p_log("Инициализация всех помощников")
    dct_2 = get_use_helper()
    dct_1 = get_helper_bag()

    if dct_2['companion']:
        dct_1['companion'].extend(dct_2['companion'])  # Добавляем надетого компаньонов

    if dct_2['horse']:
        dct_1['horse'].extend(dct_2['horse'])  # Добавляем надетого наездника

    if save_json:
        save_json_file(dct_1, "", url_helper_json)
    return dct_1


# ____________________________ Активация кармы _____________________________________________
def activate_karma(skill, count):
    def karma_worker():
        try:
            counter = count
            type_karma = get_config_value("working_karma")
            name_karma = karma[type_karma][skill]['name']
            id_karma = karma[type_karma][skill]['id_karma']
            point_karma = karma[type_karma][skill]['point']
            time_delay = 2

            while counter > 0:
                soup = BeautifulSoup(make_request(url_karma).text, 'html.parser')

                point_karma_all = get_karma_value(soup)
                day_karma = int(point_karma_all / point_karma)

                if day_karma > 0:
                    p_log(f"Кармы хватит на {day_karma} дней")
                else:
                    p_log(f"Недостаточно кармы")
                    break

                # проверка таймера
                progressbar_time = progressbar_ends(soup)
                if progressbar_time:
                    p_log(f"Карма активна еще {format_time(progressbar_time)}")
                    time.sleep(progressbar_time + time_delay)

                payload = {'activateKarmaSkill': id_karma}
                soup = BeautifulSoup(post_request(url_karma, payload).text, 'html.parser')
                p_log(f"Активирована карма: {name_karma}")

                # проверка таймера
                progressbar_time = progressbar_ends(soup)
                if progressbar_time:
                    p_log(f"Ожидание {format_time(progressbar_time)}")
                    time.sleep(progressbar_time + time_delay)
                counter -= 1

        except Exception as e:
            p_log(f"Ошибка активации кармы: {e}")

    # Запускаем и забываем
    thread = threading.Thread(target=karma_worker, daemon=True)
    thread.start()


# ____________________________ Со sliv ____________________________________________________


def make_attack(nick, heals_point=False) -> Tuple[bool, Union[bool, Response, str]]:
    if check_health(heals_point=heals_point) < 10:
        return False, False
    url_fight = url_duel_name + str(nick)
    p_log(f"Попытка атаки на {nick}")
    resp = make_request(url_fight)
    status_duel = get_status(resp)

    if status_duel == 'Дуэль':
        p_log(f"Атака {nick} произведена успешно")
        return True, resp

    while status_duel in status_list:
        p_log(f"{get_name()} status: {status_duel}")
        time_sleep()
        p_log(f"Попытка атаки на {nick}")
        resp = make_request(url_fight)
        if resp.url == url_error:
            duel_stat = handle_error(nick)
            if duel_stat:
                return True, duel_stat
            return False, resp
        status_duel = get_status(resp)

        if status_duel == 'Дуэль':
            p_log(f"Атака на {nick} произведена успешно")
            return True, resp

    duel_stat = handle_error(nick)
    if duel_stat:
        return True, duel_stat
    return False, resp


def get_status(resp):
    soup = BeautifulSoup(resp.text, 'lxml')
    return soup.find('h1').text


def get_gold_duel(resp):
    soup = BeautifulSoup(resp.text, 'lxml')
    result = int(soup.find('div', class_='fightResultsInner').find_all('em')[1].text)
    fight_status = soup.find('div', class_='fightResultsInner').find_all('em')[0].text
    p_log(f"{fight_status}. Получено {result} серебра")
    return result


def check_status_group():
    resp = make_request(url_group)
    soup = BeautifulSoup(resp.text, 'lxml')
    h4_tags = soup.find_all('h4')
    # Проверяем наличие текста 'Изменить настройки группы' в списке тегов <h4>
    for tag in h4_tags:
        if 'Изменить настройки группы' in tag.get_text(strip=True):
            return True

    return False


def handle_error(nick):
    if check_status_group():
        p_log("Мы находимся в группе, отдыхаем 10 минут")
        time_sleep()
    else:
        try:
            url_fight = url_compare + str(nick)
            resp = make_request(url_fight)
            soup = BeautifulSoup(resp.text, 'lxml')
            script_texts = soup.find_all('script')
            all_script_content = ' '.join(script.string for script in script_texts if script.string)
            pattern = re.compile(r"document\.id\('devAttackBtn'\)\.store\('tip:title',\s*'([^']+)'\)")
            match = pattern.search(all_script_content)
            if match:
                extracted_text = match.group(1)
                p_log(extracted_text)
                return extracted_text
            else:
                p_log("Нет совпадений. Проверке парсинг состония дуэли")
        except Exception as er:
            p_log("Рыцарь недоступен, либо был атакован в течение 12 часов", level='warning')
            p_log(f"Ошибка: {er}")

    return False


def update_players_gold(dict_gamer, list_of_players):
    for gamer in list_of_players:
        list_of_players[gamer].setdefault('time',
                                          dict_gamer[gamer].get('time', date) if gamer in dict_gamer else date)
        list_of_players[gamer].setdefault('win_status',
                                          dict_gamer[gamer].get('win_status',
                                                                "uncertain") if gamer in dict_gamer else "uncertain")
        list_of_players[gamer].setdefault('spoil',
                                          dict_gamer[gamer].get('spoil', 0) if gamer in dict_gamer else 0)
        list_of_players[gamer]["gold"] = get_gold_for_player(gamer)

    return list_of_players


def set_initial_gold():
    with open(url_name_json, 'r', encoding='utf-8') as file:
        list_of_players = json.load(file)

        if get_config_value(key='exclude_allow_attack'):
            list_of_players = {key: value for key, value in list_of_players.items() if value.get('allow_attack')}

    try:
        with open(GOLD_GAMER, 'rb') as file_gamer:
            p_log("Сканирование добычи игроков...")
            dict_gamer = pickle.load(file_gamer)

    except FileNotFoundError:
        p_log("Файла не существует, будет создан новый", level='warning')
        dict_gamer = {}

    filtered_dct = update_players_gold(dict_gamer, list_of_players)

    # filtered_dct = {key: dict_gamer[key] for key in list_of_players}
    with open(GOLD_GAMER, 'wb') as file_gamer:
        pickle.dump(filtered_dct, file_gamer)
        p_log("Файл игроков успешно сохранен", level='debug')


def online_tracking():
    gold_limit = get_config_value(key='gold_limit')
    with open(GOLD_GAMER, 'rb') as file_gamer:
        p_log("online_tracking", level='debug')
        dict_gamer = pickle.load(file_gamer)
        filtered_data = {key: value for key, value in dict_gamer.items() if
                         (datetime.now() - value['time']) > timedelta(hours=12)}
        if not filtered_data:
            p_log("В gamer_gold.pickle нападать не на кого")
            return False

        for gamer in sorted(filtered_data, key=lambda x: filtered_data[x]['allow_attack'], reverse=True):
            if filtered_data[gamer]['allow_attack']:
                golden_factor = get_config_value('golden_factor')
                gold = get_gold_for_player(gamer)
                gold_diff = gold - filtered_data[gamer]['gold']
                gold_diff_proc = int(gold_diff / (filtered_data[gamer]['gold_diff'] * golden_factor) * 100)
                p_log(f"{gamer} {filtered_data[gamer]['name']} накопил {gold_diff} [{gold_diff_proc}%] серебра")
            else:
                golden_factor, gold = 0, 99999999  # заглушка для "allow_attack": false
                p_log(f"Атака вне слежки на {filtered_data[gamer]['name']}")
            time_str, current_date = current_time()
            time.sleep(2)
            if gold - filtered_data[gamer]["gold"] > filtered_data[gamer]['gold_diff'] * golden_factor:
                flag, resp = make_attack(gamer, heals_point=True)
                if flag:
                    silver = get_silver(resp)
                    if silver > gold_limit - 500 and get_config_value("buy_ring"):
                        buy_ring()  # покупка кольца на аукционе
                    received_gold, win_status = (pars_gold_duel(resp, gold_info=True, win_status=True)
                                                 if isinstance(resp, Response)
                                                 else (0, resp)
                                                 )
                    dict_gamer[gamer]["time"] = current_date
                    dict_gamer[gamer]["win_status"] = win_status
                    dict_gamer[gamer]["spoil"] = received_gold

                    # Отправить в орден коровку
                    if win_status == f"{get_name()} выиграл" and received_gold > 100:
                        p_log(win_status)
                        p_log(f"{filtered_data[gamer]['name']} +{received_gold}")
                        if get_config_value(key='order_message'):
                            message = f"{filtered_data[gamer]['name']} +{received_gold}"
                            make_request(url_ordermail)
                            orden_message(message)
                            p_log("Отправлено сообщение в орден")

                    with open(GOLD_GAMER, 'wb') as file:
                        pickle.dump(dict_gamer, file)
                    if isinstance(resp, Response):
                        time_sleep()
                    return "sleep"
        return True


def online_tracking_only(reduce_flag=False):
    while True:
        status_sleep = online_tracking()
        if status_sleep == "sleep":
            continue
        if status_sleep and not reduce_flag:
            time_sleep()
        else:
            break


def reduce_experience(name_file=NICKS_GAMER, tracking=True):
    init_handle_ring_operations = handle_ring_operations(buy_ring(initial=True), False)

    with open(name_file, 'rb') as f:
        loaded_dict = pickle.load(f)
        sorted_dict = {k: v for k, v in sorted(loaded_dict.items(),
                                               key=lambda item: (
                                                   -item[1]['spoil'] if item[1]['spoil'] > 50 else float('inf'),
                                                   item[1]['time']
                                               ))}

        # number_of_attacks задается из config.ini - количесвто проводимых атак
        number_of_attacks = get_config_value(key="number_of_attacks")
        attack_flag = False

        for nick in sorted_dict:
            # online_track = 1 tracking active from config.ini
            if tracking and attack_flag and get_config_value(key="online_track"):
                online_tracking_only(reduce_flag=True)  # функция нахождения и атаки на играющих игроков

            time_str, current_date = current_time()
            difference_data = current_date - loaded_dict[nick]["time"]
            if int(difference_data.total_seconds() / 3600) >= 12:
                flag, resp = make_attack(nick)
                if flag:
                    if isinstance(resp, Response):
                        received_gold = pars_gold_duel(resp, gold_info=True)
                        silver = get_silver(resp)
                        # инициализация стоимости кольца либо покупка кольца на аукционе
                        init_handle_ring_operations(silver)
                    else:
                        received_gold = 0

                    loaded_dict[nick]["time"] = current_date
                    loaded_dict[nick]["spoil"] = received_gold
                    with open(name_file, 'wb') as file:
                        pickle.dump(loaded_dict, file)
                    if isinstance(resp, Response):
                        p_log("Ожидание 10 мин перед следующей атакой...")
                        time_sleep()
                        attack_flag = True
                    else:
                        attack_flag = False

                    number_of_attacks -= 1
                    if not number_of_attacks:
                        break
            else:
                p_log(f"{nick} не может быть атакован", level='debug')
                attack_flag = False
        # когда закончилился список из рыцаряй для слива опыта
        if tracking and get_config_value(key="online_track"):
            online_tracking_only()


def korovk_reduce_experience(name_file=NICKS_GAMER):
    def update_knight_data(loaded_dct, gamer, current_dt, spoil):
        loaded_dct[gamer]["time"] = current_dt
        loaded_dct[gamer]["spoil"] = spoil
        with open(name_file, 'wb') as file:
            pickle.dump(loaded_dct, file)

    with open(name_file, 'rb') as f:
        loaded_dict = pickle.load(f)
        sorted_dict = {k: v for k, v in sorted(loaded_dict.items(), key=lambda item: item[1]["spoil"], reverse=True)}
        list_fail = []
        while sorted_dict or list_fail:
            for nick in list(sorted_dict.keys()):
                time_str, current_date = current_time()
                difference_data = current_date - loaded_dict[nick]["time"]
                if int(difference_data.total_seconds() / 3600) >= 12:
                    flag, resp = make_attack(nick)
                    if flag:
                        received_gold = pars_gold_duel(resp, gold_info=True)
                        update_knight_data(loaded_dict, nick, current_date, received_gold)
                        del sorted_dict[nick]

                        p_log(f"Ожидание {waiting_time} сек перед следующей атакой")
                        time_sleep()
                        if list_fail:
                            break
                        online_tracking()  # функция нахождения и атаки на играющих игроков
                    else:
                        list_fail.append(nick)
                        del sorted_dict[nick]
                        continue
                else:
                    del sorted_dict[nick]
                    continue

            flag_sleep = False
            if list_fail:
                p_log(f"Список неудачных атак: {list_fail}")
                for fail_nick in list_fail[:]:
                    flag, resp = make_attack(nick)
                    last_fail_nick = list_fail[-1]
                    if flag:
                        received_gold = pars_gold_duel(resp, gold_info=True)
                        if fail_nick == last_fail_nick:
                            flag_sleep = True

                        update_knight_data(loaded_dict, fail_nick, current_date, received_gold)
                        list_fail.remove(fail_nick)

                        p_log(f"Ожидание {waiting_time} сек перед следующей атакой")
                        time_sleep()
                if not sorted_dict and not flag_sleep:
                    time_sleep()

        p_log("Все рыцари успешно пройдены")


def change_pickle_file(name_file=GOLD_GAMER):
    with open(name_file, 'rb+') as f:
        loaded_dict = pickle.load(f)
        # delete_list = list(loaded_dict.keys())
        # for i in delete_list:
        #     if loaded_dict[i]['gold'] < 500:
        #         del loaded_dict[i]
        p_log(loaded_dict)
        loaded_dict['984811']['time'] = datetime(2024, 9, 17, 18)

        f.seek(0)  # Перемещение курсора в начало файла
        f.truncate()  # Очистка содержимого файла
        pickle.dump(loaded_dict, f)
        p_log(f"Данные успешно обновлены в файл {name_file}. Всего {len(loaded_dict)} записей")


def create_pickle_file(name_file=NICKS_GAMER):
    if not os.path.exists(name_file):
        with open(name_file, 'wb') as f:
            pickle.dump({}, f)

    with open(name_file, 'rb+') as f:
        loaded_dict = pickle.load(f)
        with open(url_nicks, 'r', encoding='utf-8') as file_nicks:
            for i in file_nicks:
                id_gold = i.replace("\n", "").replace(" ", "").split(":")
                key = id_gold[0]
                gold = 0 if len(id_gold) == 1 else id_gold[1]
                if key not in loaded_dict:
                    loaded_dict[key] = {"time": date, "spoil": int(gold)}

        f.seek(0)  # Перемещение курсора в начало файла
        f.truncate()  # Очистка содержимого файла
        pickle.dump(loaded_dict, f)
        p_log(f"Данные успешно обновлены в файл {name_file}. Всего {len(loaded_dict)} записей")


def read_pickle_file(name_file=NICKS_GAMER):
    with open(f"{name_file}", 'rb') as f:
        loaded_dict = pickle.load(f)
        # dct = {k: v for k, v in sorted(loaded_dict.items(), key=lambda item: item[1]['spoil'], reverse=True)}
        # p_log(f"Коровки дадут {sum(x['spoil'] for x in loaded_dict.values())} серебра")
        for key, value in loaded_dict.items():
            p_log(f'{key}:{value}')


def test_pars():
    with open("duel.html", 'rb') as fff:
        soup = BeautifulSoup(fff, 'lxml')
        result = soup.find('h1').text
        p_log(result == 'Дуэль')


def orden_message(message):
    payload = {
        'noCache': f'{int(time.time() * 1000)}',
        'text': "",
        'subject': message
    }
    post_request(url_orden_message, payload)


# ____________________________ Верификация доступа к игре __________________________________
def account_verification(not_token=False, helper_init=True):
    response = make_request(user_url)
    set_name(response)
    get_id(response, not_token)
    # инициализация компаньонов и наездников
    if helper_init:
        all_helper(save_json=True)
