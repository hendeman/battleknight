import ast
import json
import re
from typing import Union, Tuple
from time import sleep
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime

from logs.logs import p_log
from module.all_function import time_sleep, wait_until, no_cache, dict_to_tuple, get_name_mount, get_random_value, \
    get_config_value
from module.data_pars import heals, get_status_helper, pars_healer_result, get_all_silver, pars_gold_duel, \
    check_cooldown_poit, set_name, get_id
from module.http_requests import post_request, make_request
from setting import *


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
    except Exception:
        p_log(f'Ошибка выполнения функции go_auction', level='warning')


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


def use_helper(name_companion, restore=True, direct_call=False):
    """Декоратор для использования наездника/компаньона.

        Args:
            name_companion (str): Имя наездника/компаньона из mount_list (например, 'pegasus', 'fairy').
            restore (bool): Вернуть исходного наездника/компаньона после выполнения (по умолчанию True).
            direct_call (bool): Если True, декоратор выполнится сразу без привязки к функции.
        """
    def use_companion_deco(func):
        def wrapper(*args, **kwargs):
            validate_helper = mount_list.get(name_companion, None)
            if validate_helper:
                id_helper_start = None
                id_helper = mount_list[name_companion]['id_helper']
                type_helper = mount_list[name_companion]['type_helper']
                num_inventory = "5" if type_helper == type_helper_name[0] else "6"
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
                        mount_list['bear']['id_helper']
                        if type_helper == 'horse'
                        else mount_list['squire']['id_helper']
                    )

                if helper != id_helper:
                    resp = make_request(
                        f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/wearItem/?noCache={no_cache()}"
                        f"&id={id_helper}&type=normal&invID={num_inventory}&loc=character")
                    if resp.json()['result']:
                        p_log(f"{type_helper} {get_name_mount(resp.json()['data']['id'])} надет")

                if not direct_call:
                    func(*args, **kwargs)

                if restore and get_config_value("ignor_mount"):
                    resp = make_request(
                        f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/wearItem/?noCache={no_cache()}"
                        f"&id={id_helper_start}&type=normal&invID={num_inventory}&loc=character")
                    if resp.json()['result']:
                        p_log(f"{type_helper} {get_name_mount(resp.json()['data']['id'])} надет")
            else:
                p_log(f"{name_companion} не найден в списке mount_list", level='debug')
                if not direct_call:
                    func(*args, **kwargs)

        return wrapper

    if direct_call:
        return use_companion_deco(lambda: None)()  # Автоматически вызываем

    return use_companion_deco


@use_helper('pegasus')
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


def post_dragon(length_mission, name_mission, buy_rubies=''):
    payload = {
        'chooseMission': name_mission,
        'missionArt': length_mission,
        'missionKarma': 'Good',
        'buyRubies': f"{buy_rubies}"
    }

    resp = post_request(post_url, payload)
    p_log(f"С миссии <{name_mission}> получено {pars_gold_duel(resp, gold_info=True)} серебра")
    if buy_rubies:
        p_log(f"Потрачен {buy_rubies} рубин")
    p_log(f"Всего {get_all_silver(resp)} серебра")
    check_timer()


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
    start_time = datetime.strptime(start_hour, "%H:%M").time()
    end_time = datetime.strptime(end_hour, "%H:%M").time()
    return start_time <= now <= end_time


def check_time_sleep(start_hour: str, end_hour: str, sleep_hour: str = None):
    # Получаем текущее время
    now = datetime.now().time()

    # Преобразуем строки в объекты time
    start_time = datetime.strptime(start_hour, "%H:%M").time()
    end_time = datetime.strptime(end_hour, "%H:%M").time()

    # Проверяем, находится ли текущее время в заданном диапазоне
    if start_time <= now <= end_time and sleep_hour:
        p_log(f"Отдыхаем до {sleep_hour}...")
        time_sleep(wait_until(sleep_hour))
    if start_time <= now <= end_time and sleep_hour is None:
        return True


def hide_silver(silver_limit):
    soup = BeautifulSoup(make_request(world_url).text, 'lxml')
    silver_count = int(soup.find(id='silverCount').text)
    if silver_count > silver_limit and check_treasury_timers() is None:
        return contribute_to_treasury()
    return silver_count


def get_silver():
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


def check_status_mission(name_mission, length_mission):
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    st = f"chooseMission('{length_mission}', '{name_mission}', 'Good', this)"
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


def check_mission(name_mission, length_mission, buy_rubies=''):
    check_hit_point()  # проверка количества здоровья
    dct1 = get_group_castles(get_all_items("key"))
    p_log(dct1, level='debug')
    post_dragon(
        length_mission=length_mission,
        name_mission=name_mission,
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
@use_helper('rabbit')
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


# ____________________________ Верификация доступа к игре __________________________________
def account_verification():
    response = make_request(user_url)
    set_name(response)
    get_id(response)
