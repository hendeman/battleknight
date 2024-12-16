import re
from typing import Union, Tuple
from time import sleep
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime

from logs.logs import p_log
from module.all_function import time_sleep, wait_until, no_cache, dict_to_tuple, get_name_mount, get_random_value
from module.data_pars import heals, get_status_horse
from module.http_requests import post_request, make_request
from setting import castles_all, status_list, CURRENT_TAX, mount_list, auction_castles, travel_url, mission_url, \
    post_url, map_url, url_world, world_url, healer_url, url_market, url_loot, work_url, treasury_url, deposit_url, \
    user_url, point_url, url_auctioneer, url_payout, duel_url, url_joust, url_joust_sign, url_alchemist, potion_name_buy


def print_status(from_town, where_town, how, tt):
    p_log(
        f"{'Едем' if how == 'horse' else 'Плывем'} из {castles_all[from_town]} в {castles_all[where_town]}. Ожидание {tt}")


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
    soup = BeautifulSoup(make_request(url_world).text, 'html.parser')

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


def go_auction(out):
    try:
        castle_auction = get_castle_min_time()
        post_travel(out=out, where=castle_auction)
        buy_ring()
        post_travel(out=castle_auction, where=out)
    except:
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
        p_log(f"lupatik status <{element}>")
        return progressbar_ends(soup)
    p_log("lupatik свободен")


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


# ____________Отправить рыцаря на работу work и получить награду за работу get_reward___________
def work():
    payload = {
        'hours': '8',
        'side': 'good'
    }
    make_request(work_url)
    time.sleep(1)
    post_request(work_url, payload)
    p_log("Работаем 8 часов...")
    time_sleep(28900)


def get_reward():
    make_request(work_url)
    payload = {'paycheck': 'encash'}

    post_request(work_url, payload)
    p_log(f"Награда за работу принята")


# __________ Использовать зелье use_potion, получить данные о зельях_________________________

def check_health(heals_point=False):
    resp = make_request(duel_url)
    life_count = heals(resp)
    if life_count < 10:
        if heals_point:
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
        # Получить новый список из зельев
        get_potion_bar()
    except:
        p_log("Ошибка в получении банок ХП. Отдыхаем 10 минут", level='warning')
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


def ride_pegasus(func):
    def wrapper(*args, **kwargs):
        id_horse = None
        id_pegas = mount_list['pegas']
        response = make_request(user_url)
        horse = get_status_horse(response)
        if horse and horse != id_pegas:
            id_horse = horse
            resp = make_request(
                f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/placeItem/?noCache={no_cache()}&id"
                f"={id_horse}&inventory=5&type=normal")
            if resp.json()['result']:
                p_log(f"Ездовое животное {get_name_mount(id_horse)} снято")
        if not id_horse and horse != id_pegas:
            p_log("Никакая лошадь не надета")
            id_horse = mount_list['bear']

        time_sleep(2)
        if horse != id_pegas:
            resp = make_request(f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/wearItem/?noCache={no_cache()}"
                                f"&id={id_pegas}&type=normal&invID=5&loc=character")
            if resp.json()['result']:
                p_log(f"{get_name_mount(id_pegas)} надет")

        func(*args, **kwargs)

        resp = make_request(f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/placeItem/?noCache={no_cache()}&id"
                            f"={id_pegas}&inventory=5&type=normal")
        if resp.json()['result']:
            p_log(f"{get_name_mount(id_pegas)} снят")

        time_sleep(2)
        resp = make_request(f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/wearItem/?noCache={no_cache()}"
                            f"&id={id_horse}&type=normal&invID=5&loc=character")
        if resp.json()['result']:
            p_log(f"Ездовое животное {get_name_mount(id_horse)} надето")

    return wrapper


@ride_pegasus
def post_travel(out='', where='', how='horse'):
    payload = {
        'travelwhere': f'{where}',
        'travelhow': f'{how}',
        'travelpremium': 0
    }
    p_log(payload, level='debug')
    responce_redirect = post_request(travel_url, payload)  # ответ редирект
    timer_travel = check_progressbar(responce_redirect)
    if not timer_travel:
        p_log("Рыцарь не уехал в другой город!", level='warning')
    else:
        print_status(out, where, how, seconds_to_hhmmss(timer_travel))

    check_timer()


def post_dragon(length_mission, name_mission, buy_rubies=''):
    payload = {
        'chooseMission': name_mission,
        'missionArt': length_mission,
        'missionKarma': 'Good',
        'buyRubies': f"{buy_rubies}"
    }

    post_request(post_url, payload)
    p_log(f"Атака выполнена успешно, потрачено {buy_rubies if buy_rubies else '0'} рубинов")

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


def group_time(start_hour: str, end_hour: str):
    now = datetime.now().time()
    start_time = datetime.strptime(start_hour, "%H:%M").time()
    end_time = datetime.strptime(end_hour, "%H:%M").time()
    return start_time <= now <= end_time


def check_time_sleep(start_hour: str, end_hour: str, sleep_hour: str):
    # Получаем текущее время
    now = datetime.now().time()

    # Преобразуем строки в объекты time
    start_time = datetime.strptime(start_hour, "%H:%M").time()
    end_time = datetime.strptime(end_hour, "%H:%M").time()

    # Проверяем, находится ли текущее время в заданном диапазоне
    if start_time <= now <= end_time:
        p_log(f"Отдыхаем до {sleep_hour}...")
        time_sleep(wait_until(sleep_hour))


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


def check_mission(name_mission, length_mission):
    check_hit_point()  # проверка количества здоровья
    dct1 = get_group_castles(get_all_items("key"))
    p_log(dct1, level='debug')
    post_dragon(
        length_mission=length_mission,
        name_mission=name_mission
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
    post_request(healer_url, payload)
    p_log("Зелье мудрости куплено")


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

def get_inventory_slots(num_inv: Union[int, Tuple[int, int]] = None):
    # Определяем диапазон инвентарей
    if isinstance(num_inv, tuple) and len(num_inv) == 2:
        inventories = range(num_inv[0], num_inv[1] + 1)
    elif isinstance(num_inv, int):
        inventories = [num_inv]
    else:
        inventories = range(1, 5)  # По умолчанию, если num_inv не задан
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
            inventory = get_inventory_slots()
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


def buy_ring(tariff_travel=0):
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
    if month_number % 5 == 0:
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
        except:
            p_log("Ошибка регистрации на турнир")


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
