import re
from time import sleep
import random
from bs4 import BeautifulSoup
from datetime import datetime

from game_play import check_progressbar, check_treasury_timers, contribute_to_treasury, ride_pegasus
from logs.logs import p_log
from module.all_function import time_sleep, wait_until, no_cache, dict_to_tuple
from module.data_pars import heals
from module.http_requests import post_request, make_request
from setting import castles_all, status_list

travel_url = 'https://s32-ru.battleknight.gameforge.com:443/world/startTravel'
mission_url = 'https://s32-ru.battleknight.gameforge.com/world/location'
post_url = 'https://s32-ru.battleknight.gameforge.com/world/location/'
map_url = 'https://s32-ru.battleknight.gameforge.com/world/map'
world_url = 'https://s32-ru.battleknight.gameforge.com/world'
healer_url = 'https://s32-ru.battleknight.gameforge.com/zanyhealer/buyAndUsePotion/'
url_market = 'https://s32-ru.battleknight.gameforge.com/market/merchant/artefacts'
url_loot = 'https://s32-ru.battleknight.gameforge.com/user/loot/'


def print_status(from_town, where_town, how):
    p_log(f"{'Едем' if how == 'horse' else 'Плывем'} из {castles_all[from_town]} в {castles_all[where_town]}")


def check_timer():
    response = make_request(mission_url)
    soup = BeautifulSoup(response.text, 'lxml')
    response = soup.find('h1').text.strip()
    if response in status_list:
        time_sleep(check_progressbar())


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
        print_status(out, where, how)

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
        p_log(f"Отдываем до {sleep_hour}...")
        time_sleep(wait_until(sleep_hour))


def hide_silver(silver_limit):
    soup = BeautifulSoup(make_request(world_url).text, 'lxml')
    silver_count = int(soup.find(id='silverCount').text)
    if silver_count > silver_limit and check_treasury_timers() is None:
        contribute_to_treasury()


def check_status_mission(name_mission, length_mission):
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    st = f"chooseMission('{length_mission}', '{name_mission}', 'Good', this)"
    a_tags = soup.find_all('a', onclick=lambda onclick: onclick and st in onclick)
    return a_tags


def get_all_keys():
    pattern = re.compile(r'^Clue\d+_closed$')
    item_key_list = {}  # формат записи 22273032: {'item_pic': 'Clue01_closed', 'location': 'TradingPostFour'}
    for i in range(3, 5):
        url = (f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/getInventory/?noCache={no_cache()}'
               f'&inventory={i}&loc=character')
        resp = make_request(url)

        try:
            if resp.json()['result']:
                for item in resp.json()['items']:
                    if pattern.match(item['item_pic']):
                        item_key_list[item['item_id']] = {'item_pic': item['item_pic'],
                                                          'location': item['clue_data']['location']}
        except ValueError:
            p_log("Ошибка ставки. Ошибка json(). Неверный запрос получения инвентаря", level='warning')
        sleep(1)
    p_log("Словарь с ключами успешно сформирован", level='debug')
    return item_key_list


def check_mission(name_mission, length_mission):
    check_hit_point()  # проверка количества здоровья
    dct1 = get_group_castles(get_all_keys())
    p_log(dct1, level='debug')
    post_dragon(
        length_mission=length_mission,
        name_mission=name_mission
    )
    make_request(mission_url)  # Запрос в миссии для обновления ключей
    dct2 = get_group_castles(get_all_keys())
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


def do_matrix_inventory(data):
    rows = 8
    cols = 7
    matrix = [data[i * rows:(i + 1) * rows] for i in range(cols)]
    return matrix


# __________________ Получаем случайное значение номера сумки и координаты свободного слота __________________

def choose_random_coor(dct):
    if dct:
        random_key = random.choice(list(dct.keys()))
        random_value = random.choice(dct[random_key])
        result = {random_key: random_value}
        return result
    else:
        print("Нет свободных слотов в сумке")


# _______________________ Получаем данные заполненности инвентаря в 3 и 4 сумке _______________________________

def get_inventory_slots():
    item_key_list = {}
    for i in range(3, 5):
        url_inventory = (f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/getInventory/?noCache={no_cache()}'
                         f'&inventory={i}&loc=character')
        resp = make_request(url_inventory)

        try:
            result = resp.json()
            if resp.json()['result']:
                item_key_list[f"{i}"] = do_matrix_inventory(result['inventory'])
        except ValueError:
            print("Ошибка ставки. Ошибка json(). Неверный запрос получения инвентаря")
        sleep(1)
    return item_key_list


# ________________________________ Преобразование  данных инвентаря в матричный вид _________________

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
    print(coordinates_dict)
    return coordinates_dict


# _____________________________ Проверить, если ли общий ключ в продаже ____________________________________

def get_key_market():
    soup = BeautifulSoup(make_request(url_market).text, 'lxml')
    items_market = soup.find(id='merchItemLayer')
    small_key = items_market.find('div', class_='itemClue01_closed')
    element_id = small_key['id'] if small_key and 'id' in small_key.attrs else None
    if element_id:
        id_key = ''.join(filter(lambda x: x.isdigit(), element_id))
        print(f"В продаже имеется общий ключ {id_key}")
        return [id_key]
    print('Нет ключей в продаже')


def get_key_loot():
    soup = BeautifulSoup(make_request(url_loot).text, 'lxml')
    items_loot = soup.find(id='lootContent')
    pattern = re.compile(r'itemClue\d+_closed')
    keys_list = []
    for item in items_loot.find_all('div'):
        if pattern.search(' '.join(item.get('class', []))):
            id_key = ''.join(filter(lambda x: x.isdigit(), item['id']))
            keys_list.append(id_key)  # Сохраняем id элемента
    if keys_list:
        print(f"Доступные ключи в сундуке добычи: {keys_list}")
        return keys_list
    print("В сундуке добычи нет ключей")


# ____________________________ Основная функция покупки ключа на рынке ____________________________________

def move_key(how='buy'):
    id_key = get_key_loot() if how == 'loot' else get_key_market()
    if id_key:
        for item in id_key:
            inventory = get_inventory_slots()
            free_coord = get_free_coord(inventory)
            dct_coor = choose_random_coor(free_coord)
            if dct_coor:
                inv, coor = next(iter(dct_coor.items()))
                print(f"Попытка переместить ключ {item} в сумку {inv}, ячейка {coor}")
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
