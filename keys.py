import re

from bs4 import BeautifulSoup

from logs.logs import p_log, setup_logging
from module.game_function import post_travel, my_place, check_hit_point, hide_silver, check_status_mission, \
    get_all_keys, check_mission, get_group_castles
from module.http_requests import make_request
from module.all_function import time_sleep
from setting import castles_all, castles_island, castles, world_url, map_url


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
                    hide_silver(silver_limit=5000)
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
    setup_logging()
    keys_search(event='Ключи', rubies=False, length_mission='small')
