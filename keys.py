import re

from bs4 import BeautifulSoup

from dragon import check_timer
from logs.logs import p_log
from module.all_function import no_cache
from module.http_requests import make_request, post_request
from module.all_function import time_sleep
from setting import castles_all, castles_island, castles

world_url = 'https://s32-ru.battleknight.gameforge.com/world'
post_url = 'https://s32-ru.battleknight.gameforge.com/world/location/'
mission_url = 'https://s32-ru.battleknight.gameforge.com/world/location'
map_url = 'https://s32-ru.battleknight.gameforge.com/world/map'
travel_url = 'https://s32-ru.battleknight.gameforge.com:443/world/startTravel'


def print_status(from_town, where_town, how):
    p_log(f"{'Едем' if how == 'horse' else 'Плывем'} из {castles_all[from_town]} в {castles_all[where_town]}")


def post_travel(out='', where='', how='horse'):
    payload = {
        'travelwhere': f'{where}',
        'travelhow': f'{how}',
        'travelpremium': 0
    }
    p_log(payload)
    print_status(out, where, how)
    post_request(travel_url, payload)

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


def heals(resp):
    soup = BeautifulSoup(resp.text, 'lxml')
    try:
        life_count_element = int(soup.find(id="lifeCount").text.split()[0])
        print(f"Количество здоровья: {life_count_element}")
        return life_count_element
    except Exception:
        # p_log("Error parsing current health", level='warning')
        print("Плохо")


def check_hit_point():
    while True:
        response = make_request(world_url)
        if heals(response) < 20:
            print("Отдыхаем 10 минут, пока не восстановится здоровье")
            time_sleep(610)
        else:
            break


def check_status_mission(name_mission, length_mission):
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    st = f"chooseMission('{length_mission}', '{name_mission}', 'Good', this)"
    a_tags = soup.find_all('a', onclick=lambda onclick: onclick and st in onclick)
    return a_tags


def travel_mission(length_mission='small'):
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    complete_mission(soup, length_mission, cog_plata=True)


def complete_mission(soup, length_mission, cog_plata=False):
    name_mission, a_tags = find_mission(soup, length_mission)
    flag = False
    for mission in name_mission:
        while True:
            if 'disabledSpecialBtn' in a_tags[0].get('class', []):
                print("Миссий нет. Ждем час...")
                time_sleep(3600)
                a_tags = check_status_mission(name_mission=mission, length_mission=length_mission)
            else:
                print("Есть доступные миссии")
                if not cog_plata:
                    differences = check_mission(name_mission=mission, length_mission=length_mission)
                    if not differences:
                        print(f"Если словари одинаковые, то ключ не распокавался или удалился, идет на след. миссию")
                        break
                    a_tags = check_status_mission(name_mission=mission, length_mission=length_mission)
                    print(f"Если ключ пропал или распаковался, то проходим ту же миссии")
                else:
                    a_tags = check_status_mission(name_mission=mission, length_mission=length_mission)
                    silver_count = int(soup.find(id='silverCount').text)
                    if silver_count >= 800:
                        flag = True
                        break
        if flag:
            break


def find_mission(soup, length_mission):
    name_missions = []
    st_pattern = f"chooseMission\\('{length_mission}', '([a-zA-Z]+)', 'Good', this\\);"
    a_tags = soup.find_all('a', onclick=lambda onclick: onclick and re.match(st_pattern, onclick))
    for tag in a_tags:
        onclick_value = tag['onclick']
        match = re.search(st_pattern, onclick_value)
        if match:
            nm = match.group(1)  # Извлекаем значение name_mission
            name_missions.append(nm)  # Добавляем в список
    # name_mission = random.choice(name_missions)
    return name_missions, a_tags


def get_all_keys():
    pattern = re.compile(r'^Clue\d+_closed$')
    item_key_list = {}  # формат записи 22273032: {'item_pic': 'Clue01_closed', 'location': 'TradingPostFour'}
    for i in range(3, 5):
        url = f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/getInventory/?noCache={no_cache()}&inventory={i}&loc=character'
        resp = make_request(url)

        try:
            if resp.json()['result']:
                for item in resp.json()['items']:
                    if pattern.match(item['item_pic']):
                        item_key_list[item['item_id']] = {'item_pic': item['item_pic'],
                                                          'location': item['clue_data']['location']}
        except ValueError:
            print("Ошибка ставки. Ошибка json(). Неверный запрос получения инвентаря")
    return item_key_list


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


def check_mission(name_mission, length_mission):
    check_hit_point()  # проверка количества здоровья
    dct1 = get_group_castles(get_all_keys())
    post_dragon(
        length_mission=length_mission,
        name_mission=name_mission
    )
    dct2 = get_group_castles(get_all_keys())
    differences = set(dct1.items()) ^ set(dct2.items())
    return differences


def my_place():
    response = make_request(mission_url)
    soup = BeautifulSoup(response.text, 'lxml')
    place = soup.find('h1').text.strip()
    for key, value in castles_all.items():
        if value == place:
            return value, key
    return place, None


def keys_search(event, rubies, length_mission):
    # check_time_sleep(start_hour='00:00', end_hour='02:00', sleep_hour='07:00')
    place, my_town = my_place()  # Джаро, VillageFour
    p_log(f"Я нахожусь в {place}")
    all_keys = get_all_keys()
    group_castles = get_group_castles(all_keys)
    name_max_city = max(group_castles, key=lambda k: group_castles[k]['count'])
    response = make_request(map_url)
    soup = BeautifulSoup(response.text, 'lxml')
    silver_count = int(soup.find(id='silverCount').text)
    if not name_max_city:
        raise f"Нет доступных ключей"
    p_log(f"Максимальное количество ключей находится в {castles_all[name_max_city]}")

    if (my_town in castles_island and name_max_city in castles_island) or (
            my_town in castles and name_max_city in castles):
        if my_town == name_max_city:
            p_log(f"Вы в городе с максимальным количеством ключей!")
            check_hit_point()  # проверка количества здоровья
            travel_mission(length_mission=length_mission)
        else:
            post_travel(out=my_town, where=name_max_city)

    if my_town in castles_island and name_max_city in castles:
        if my_town == 'HarbourTwo':
            if silver_count < 800:
                travel_mission(length_mission='small')
            post_travel(out='HarbourTwo', where='HarbourOne', how='cog')
        else:
            post_travel(out=my_town, where='HarbourTwo')

    if my_town in castles and name_max_city in castles_island:
        if my_town == 'HarbourOne':
            if silver_count < 800:
                travel_mission(length_mission='small')
            post_travel(out='HarbourOne', where='HarbourTwo', how='cog')
        else:
            post_travel(out=my_town, where='HarbourOne')


if __name__ == "__main__":
    keys_search(event='Ключи', rubies=False, length_mission='small')
