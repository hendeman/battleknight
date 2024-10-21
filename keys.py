import multiprocessing
import re

from bs4 import BeautifulSoup

from game_play import check_progressbar, run_process_for_hours
from group import go_group
from logs.logger_process import logger_process
from logs.logs import p_log, setup_logging
from module.game_function import post_travel, my_place, check_hit_point, hide_silver, check_status_mission, \
    get_all_keys, check_mission, get_group_castles, post_dragon, check_time_sleep, group_time, move_key
from module.http_requests import make_request
from module.all_function import time_sleep, format_time, get_save_castle, clear_save_castle, write_save_castle
from setting import castles_all, castles_island, castles, world_url, map_url
from sliv import reduce_experience


# ___________________ Выполнить миссию. Флаг cog_plata=True значит миссия для переправы __________


def complete_mission(length_mission, current_castle, save_mission=None, cog_plata=False):
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    name_mission, a_tags = find_mission(soup, length_mission)
    if save_mission:
        element = name_mission.index(save_mission)
        name_mission = name_mission[element:]
    flag = False
    for mission in name_mission:
        while True:
            # ____________________________ Ночной перерыв _________________________________
            check_time_sleep(start_hour='00:00', end_hour='02:00', sleep_hour='07:00')
            # _______________________ Время для групповой миссии __________________________
            check_time_sleep(start_hour='19:30', end_hour='21:29', sleep_hour='21:30')

            if group_time(start_hour='21:29', end_hour='21:35'):
                go_group(3600)
                timer_group = check_progressbar()
                if timer_group:
                    p_log(f"Ожидание после группы {format_time(timer_group)}. Ожидаем...")
                time_sleep(timer_group)
            # _____________________________________________________________________________

            if 'disabledSpecialBtn' in a_tags[0].get('class', []):
                p_log("Миссий нет. Ждем 2 часа...")
                #  _____ Запускаем новый процесс, который 2 часа будет сливать опыт и следить за врагами _____
                run_process_for_hours(reduce_experience, 2, 'reduce_experience')

                a_tags = check_status_mission(name_mission=mission, length_mission=length_mission)
            else:
                p_log("Есть доступные миссии")
                if not cog_plata:
                    p_log(f"Будет произведена попытка пройти {mission} миссию")
                    differences = check_mission(name_mission=mission, length_mission=length_mission)
                    if not differences:
                        p_log(f"Миссия {mission} не открыла ключ. Идем на другую")
                        a_tags = check_status_mission(name_mission=mission, length_mission=length_mission)
                        break
                    a_tags = check_status_mission(name_mission=mission, length_mission=length_mission)
                    hide_silver(silver_limit=5000)  # внести в казну
                    current_dict_key = get_group_castles(get_all_keys())
                    if current_dict_key[current_castle]['item_pic'] is None:
                        print(f"В городе {current_castle} все ключи открыты")
                        flag = True
                        clear_save_castle()  # очистка файла с сохранением локации
                        break
                    p_log(f"Миссия {mission} открыла ключ. Миссия будет выполнена повторно")
                    write_save_castle(current_castle, mission)
                else:
                    a_tags = check_status_mission(name_mission=mission, length_mission=length_mission)
                    soup = BeautifulSoup(make_request(world_url).text, 'lxml')
                    silver_count = int(soup.find(id='silverCount').text)
                    check_hit_point()
                    post_dragon(
                        length_mission=length_mission,
                        name_mission=mission
                    )
                    if silver_count >= 800:
                        flag = True
                        break
        if flag:
            p_log(f"В {current_castle} закончились все ключи")
            try:
                move_key(how='buy')  # купить ключ
                move_key(how='loot')  # переместить ключи из сундука добычи
            except:
                p_log("Ошибка выполнения move_key", level='warning')
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

    save_castle = get_save_castle()  # проверяем, если замок в файле
    if save_castle:
        name_max_city, save_mission = next(iter(save_castle.items()))
    else:
        name_max_city = max(group_castles, key=lambda k: group_castles[k]['count'])
        save_mission = None

    response = make_request(map_url)
    soup = BeautifulSoup(response.text, 'lxml')
    silver_count = int(soup.find(id='silverCount').text)
    if not name_max_city:
        raise f"Нет доступных ключей"
    p_log(f"Максимальное количество ключей находится в "
          f"{castles_all[name_max_city]}, {group_castles[name_max_city]['count']} ключей")

    if (my_town in castles_island and name_max_city in castles_island) or (
            my_town in castles and name_max_city in castles):
        if my_town == name_max_city:
            p_log(f"Вы в городе с максимальным количеством ключей!")
            check_hit_point()  # проверка количества здоровья
            complete_mission(length_mission=length_mission, current_castle=name_max_city, save_mission=save_mission)
        else:
            post_travel(out=my_town, where=name_max_city)

    if my_town in castles_island and name_max_city in castles:
        if my_town == 'HarbourTwo':
            if silver_count < 800:
                complete_mission(length_mission='small', current_castle=name_max_city, cog_plata=True)
            post_travel(out='HarbourTwo', where='HarbourOne', how='cog')
        else:
            post_travel(out=my_town, where='HarbourTwo')

    if my_town in castles and name_max_city in castles_island:
        if my_town == 'HarbourOne':
            if silver_count < 800:
                complete_mission(length_mission='small', current_castle=name_max_city, cog_plata=True)
            post_travel(out='HarbourOne', where='HarbourTwo', how='cog')
        else:
            post_travel(out=my_town, where='HarbourOne')


if __name__ == "__main__":
    queue = multiprocessing.Queue()
    logging_process = multiprocessing.Process(target=logger_process, args=(queue,))
    logging_process.start()
    setup_logging(queue)  # Настраиваем логирование с использованием очереди

    count = 15  # Чисто для избавления от вечного цикла
    while count:
        keys_search(event='Ключи', rubies=False, length_mission='small')
        count -= 1
    p_log("Количесвто выполнений keys_search превысило допустимое")

    # Завершение дочернего процесса логирования
    queue.put(None)  # Отправляем сигнал для завершения
    logging_process.join()  # Ждем завершения дочернего процесса
