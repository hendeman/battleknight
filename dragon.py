import multiprocessing
import random
import re

from functools import partial

from bs4 import BeautifulSoup

from group import go_group
from logs.logger_process import logger_process
from logs.logs import p_log, setup_logging
from module.all_function import time_sleep, wait_until, format_time, time_sleep_main
from module.game_function import check_timer, post_dragon, check_hit_point, post_travel, my_place, check_time_sleep, \
    post_healer, check_progressbar
from module.http_requests import make_request
from setting import castles_all, castles_island, castles, world_url, map_url, url_zany_healer

event_list = {
    'dragon': {'icon': 'DragonIcon', 'name': 'DragonEventGreatDragon'},
    'healer': {'icon': 'ZanyHealerIcon', 'name': ''}
}


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
    name_mission = random.choice(name_missions)
    return name_mission, a_tags


def complete_mission(soup, length_mission, cog_plata=False):
    name_mission, a_tags = find_mission(soup, length_mission)
    while True:
        if 'disabledSpecialBtn' in a_tags[0].get('class', []):
            p_log("Миссий нет. Ждем час...")
            time_sleep(3600)
            response = make_request(world_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            st = f"chooseMission('{length_mission}', '{name_mission}', 'Good', this)"
            a_tags = soup.find_all('a', onclick=lambda onclick: onclick and st in onclick)
        else:
            p_log("Есть доступные миссии")
            check_hit_point()  # проверка количества здоровья
            post_dragon(
                length_mission=length_mission,
                name_mission=name_mission
            )
            response = make_request(world_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            st = f"chooseMission('{length_mission}', '{name_mission}', 'Good', this)"
            a_tags = soup.find_all('a', onclick=lambda onclick: onclick and st in onclick)
            silver_count = int(soup.find(id='silverCount').text)
            if silver_count >= 800:
                if not cog_plata:
                    make_request(url_zany_healer)
                    post_healer(5)
                break


def process_page(event, rubies, length_mission, name_mission):
    break_outer = False
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    a_tags = []

    if event == 'dragon':
        st = f"chooseMission('{length_mission}', '{name_mission}', 'Good', this)"
        a_tags = soup.find_all('a', onclick=lambda onclick: onclick and st in onclick)

    if event == 'healer':
        silver_count = int(soup.find(id='silverCount').text)
        if silver_count >= 800:
            make_request(url_zany_healer)
            post_healer(5)
        else:
            name_mission, a_tags = find_mission(soup, length_mission)

    if a_tags:
        for a_tag in a_tags:
            if rubies and 'disabledSpecialBtn' in a_tag.get('class', []):
                buy_rubies_tags = soup.find_all('a', class_='devLarge missionBuyRubies toolTip',
                                                onclick=lambda onclick: onclick and (
                                                        "chooseMission('large', 'DragonEventGreatDragon', 'Good', this, '1')" in onclick
                                                        or "chooseMission('large', 'DragonEventGreatDragon', 'Good', this, '2')" in onclick
                                                        or "chooseMission('large', 'DragonEventGreatDragon', 'Good', this, '3')" in onclick))
                if buy_rubies_tags:
                    for buy_rubies_tag in reversed(buy_rubies_tags):
                        onclick_value = buy_rubies_tag.get('onclick')
                        p_log(onclick_value)
                        if onclick_value:
                            parts = onclick_value.split(',')
                            if len(parts) > 4:
                                fifth_argument = parts[4].strip().strip("');")

                                post_dragon(
                                    length_mission=length_mission,
                                    name_mission=name_mission,
                                    buy_rubies=fifth_argument
                                )
                                break_outer = True
                                break
                    if break_outer:
                        break
        else:
            complete_mission(soup, length_mission)

    else:
        if event == 'dragon':
            p_log('Не удалось найти тег <a> с нужным атрибутом onclick.')


def travel_mission(length_mission='small'):
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    complete_mission(soup, length_mission, cog_plata=True)


def event_search(event, rubies, length_mission):
    check_time_sleep(start_hour='00:00', end_hour='02:00', sleep_hour='07:00')
    place, my_town = my_place()  # Джаро, VillageFour
    p_log(f"Я нахожусь в {place}")
    response = make_request(map_url)
    soup = BeautifulSoup(response.text, 'lxml')
    silver_count = int(soup.find(id='silverCount').text)
    dragon_town = soup.find(id=event_list[event]['icon']).get('class')[0]
    if not dragon_town:
        raise f"{event} нет на карте"
    p_log(f"{event} находится в {castles_all[dragon_town]}")

    if (my_town in castles_island and dragon_town in castles_island) or (my_town in castles and dragon_town in castles):
        if my_town == dragon_town:
            p_log(f"Вы в городе с {event}!")
            check_hit_point()  # проверка количества здоровья
            process_page(
                event=event,
                rubies=rubies,
                length_mission=length_mission,
                name_mission=event_list[event]['name']
            )  # атака на дракона
        else:
            post_travel(out=my_town, where=dragon_town)

    if my_town in castles_island and dragon_town in castles:
        if my_town == 'HarbourTwo':
            if silver_count < 800:
                travel_mission(length_mission='small')
            post_travel(out='HarbourTwo', where='HarbourOne', how='cog')
        else:
            post_travel(out=my_town, where='HarbourTwo')

    if my_town in castles and dragon_town in castles_island:
        if my_town == 'HarbourOne':
            if silver_count < 800:
                travel_mission(length_mission='small')
            post_travel(out='HarbourOne', where='HarbourTwo', how='cog')
        else:
            post_travel(out=my_town, where='HarbourOne')


def wrapper_function(func1):
    while True:
        try:
            func1()  # Запускаем первую функцию с аргументами
        except Exception as e:
            print(f"Исключение в {func1}:", e)
            break


if __name__ == "__main__":
    queue = multiprocessing.Queue()
    logging_process = multiprocessing.Process(target=logger_process, args=(queue,))
    logging_process.start()

    setup_logging(queue)  # Настраиваем логирование с использованием очереди

    check_timer()
    kwargs = {
        'event': 'healer',
        'rubies': False,
        'length_mission': 'small'
    }
    partial_event_search = partial(event_search, **kwargs)
    while True:
        p_log(f"Запуск {'healer'} процесса...")
        process = multiprocessing.Process(target=wrapper_function, args=(partial_event_search,))
        process.start()
        p_log(f"Процесс {'healer'} будет работать до 19:30...")
        time_sleep_main(wait_until('19:30'), interval=1800)
        p_log(f"Остановка {'healer'} процесса...")
        process.terminate()
        process.join()
        check_timer()
        # Ожидание до 21:30 для синхронизации. 2 часа должно быть достаточно в большинстве случаев
        time_begin = wait_until("21:30")
        p_log(f"До начала группы осталось {format_time(time_begin)}. Ожидаем...")
        time_sleep(time_begin)
        # Создаем группу
        go_group(3600)
        timer_group = check_progressbar()
        if timer_group:
            p_log(f"Ожидание после группы {format_time(timer_group)}. Ожидаем...")
            time_sleep(timer_group)
# process_page(url)
# check_timer()
# post_travel(where='HarbourTwo', how='horse')
