import multiprocessing
import re

from bs4 import BeautifulSoup

from game_play import run_process_for_hours
from logs.logger_process import logger_process
from logs.logs import p_log, setup_logging
from module.game_function import post_travel, my_place, check_hit_point, hide_silver, check_status_mission, \
    get_all_items, check_mission, get_group_castles, post_dragon, check_time_sleep, is_time_between, move_item, \
    get_silver, \
    check_progressbar, go_auction, buy_ring, account_verification, reduce_experience, online_tracking_only
from module.group import go_group
from module.http_requests import make_request
from module.all_function import time_sleep, format_time, get_save_castle, clear_save_castle, write_save_castle, \
    get_config_value, time_sleep_main
from setting import castles_all, castles_island, castles, world_url, map_url, auction_castles


# ___________________ Выполнить миссию. Флаг cog_plata=True значит миссия для переправы __________


def complete_mission(current_castle, save_mission=None, cog_plata=False):
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'lxml')
    name_mission = find_mission(soup)
    if save_mission:
        element = name_mission.index(save_mission)
        name_mission = name_mission[element:]
    flag = False
    flag_cog = False

    def process_mission_with_keys(mission, buy_rubies=''):
        """
        Общая функция для обработки миссий с проверкой ключей.

        :param mission: Название миссии.
        :param buy_rubies: Параметр для функции check_mission (может быть None или '1').
        :return: Кортеж (остановить_цикл, флаг_ключа).
        """
        p_log(f"Будет произведена попытка пройти {mission} миссию")
        differences = check_mission(name_mission=mission, buy_rubies=buy_rubies)
        if not differences:
            p_log(f"Миссия {mission} не открыла ключ. Идем на другую")
            return True, False  # Прерываем цикл, так как миссия не открыла ключ

        current_dict_key = get_group_castles(get_all_items("key"))
        if current_castle != 'VillageOne' and current_castle not in current_dict_key:
            p_log(f"В городе {current_castle} все ключи открыты")
            return True, True  # Прерываем цикл, так как все ключи уже открыты

        p_log(f"Миссия {mission} открыла ключ. Миссия будет выполнена повторно")
        p_log(f"В данной локации осталось ещё {current_dict_key.get(current_castle, {}).get('count', 0)} ключей")
        write_save_castle(current_castle, mission)
        return False, False  # Не прерываем цикл, продолжаем выполнение миссий

    p_log(f"В {current_castle} имеются следующие миссии {name_mission}")
    for mission in name_mission:
        while True:
            gold_limit = get_config_value(key='gold_limit')

            # ____________________________ Ночной перерыв _________________________________
            check_time_sleep(start_hour='00:00', end_hour='02:00', sleep_hour='07:00')
            # _______________________ Время для групповой миссии __________________________
            check_time_sleep(start_hour='19:20', end_hour='21:29', sleep_hour='21:30')

            if is_time_between(start_hour='21:29', end_hour='21:35'):
                go_group(3600)
                timer_group = check_progressbar()
                if timer_group:
                    p_log(f"Ожидание после группы {format_time(timer_group)}. Ожидаем...")
                time_sleep(timer_group)
            # _____________________________________________________________________________

            time_sleep(check_progressbar())
            check_hit_point()
            a_tags = check_status_mission(name_mission=mission)

            if 'disabledSpecialBtn' in a_tags[0].get('class', []):
                p_log("Закончились бесплатные миссии")
                if get_config_value(key='mission_for_rubies'):
                    stop_cycle, flag = process_mission_with_keys(mission, "1")
                    p_log(f"stop_cycle={stop_cycle}, flag={flag}", level="debug")
                    if stop_cycle:
                        break
                else:
                    silver_count = hide_silver(silver_limit=gold_limit)  # внести в казну

                    if silver_count > gold_limit:
                        not_auction_timer = any(
                            [check_time_sleep(start_hour='10:45', end_hour='12:45', sleep_hour=None),
                             check_time_sleep(start_hour='22:45', end_hour='23:59', sleep_hour=None)])
                        if current_castle not in auction_castles and not not_auction_timer:
                            go_auction(out=current_castle)
                        else:
                            if get_config_value("buy_ring"):
                                buy_ring()

                    p_log("Миссий нет. Ждем 1 час 45 мин...")
                    #  _____ Запускаем новый процесс, который 1 час 45 мин будет сливать опыт и следить за врагами _____
                    if get_config_value(key="online_tracking_only"):
                        if get_config_value(key="reduce_experience"):
                            run_process_for_hours(reduce_experience, 1.75, 'reduce_experience')
                        else:
                            run_process_for_hours(online_tracking_only, 1.75, 'online_tracking_only')
                    else:
                        time_sleep_main(int(1.45 * 60 * 60))

            else:
                p_log("Есть доступные миссии")
                if not cog_plata:
                    stop_cycle, flag = process_mission_with_keys(mission)
                    p_log(f"stop_cycle={stop_cycle}, flag={flag}", level="debug")
                    if stop_cycle:
                        break
                else:
                    post_dragon(name_mission=mission, sleeping=False)
                    silver_count = get_silver()
                    if silver_count >= 800:
                        flag_cog = True
                        break
        silver_count = hide_silver(silver_limit=gold_limit)  # внести в казну
        if silver_count > gold_limit and get_config_value("buy_ring"):
            buy_ring(tariff_travel=1000)  # оставить 1000 серебра на переправу
        if flag_cog or flag:
            break
    if not flag_cog:
        p_log(f"В {current_castle} закончились все ключи")
        clear_save_castle()  # очистка файла с сохранением локации
        silver_count = get_silver()
        try:
            if silver_count >= 140:
                move_item(how='buy')  # купить ключ
            move_item(how='loot')  # переместить ключи из сундука добычи
        except Exception as er:
            p_log(f"Ошибка выполнения move_item: {er}", level='warning')


def find_mission(soup):
    name_missions = []
    mission_karma = get_config_value("working_karma").capitalize()
    length_mission = get_config_value("mission_duration")
    st_pattern = f"chooseMission\\('{length_mission}', '([a-zA-Z]+)', '{mission_karma}', this\\);"
    a_tags = soup.find_all('a', onclick=lambda onclick: onclick and re.match(st_pattern, onclick))
    for tag in a_tags:
        onclick_value = tag['onclick']
        match = re.search(st_pattern, onclick_value)
        if match:
            nm = match.group(1)  # Извлекаем значение name_mission
            name_missions.append(nm)  # Добавляем в список
    # name_mission = random.choice(name_missions)
    return name_missions


def keys_search():
    time_sleep(check_progressbar())  # проверить статус
    # check_time_sleep(start_hour='00:00', end_hour='02:00', sleep_hour='07:00')
    place, my_town = my_place()  # Джаро, VillageFour
    p_log(f"Я нахожусь в {place}")
    all_keys = get_all_items("key")
    group_castles = get_group_castles(all_keys)

    save_castle = get_save_castle()  # проверяем, если замок в файле
    if save_castle:
        name_max_city, save_mission = next(iter(save_castle.items()))
    else:
        try:
            name_max_city = max(group_castles, key=lambda k: group_castles[k]['count'])
            save_mission = None
        except ValueError:
            p_log(group_castles, level="debug")
            raise ValueError("Все ключи открыты")

    response = make_request(map_url)
    soup = BeautifulSoup(response.text, 'lxml')
    silver_count = int(soup.find(id='silverCount').text)
    if not name_max_city:
        raise f"Нет доступных ключей"
    p_log(f"Максимальное количество ключей находится в "
          f"{castles_all[name_max_city]}, {group_castles.get(name_max_city, {}).get('count', 0)} ключей")

    if (my_town in castles_island and name_max_city in castles_island) or (
            my_town in castles and name_max_city in castles):
        if my_town == name_max_city:
            p_log(f"Вы в городе с максимальным количеством ключей!")
            check_hit_point()  # проверка количества здоровья
            complete_mission(current_castle=name_max_city, save_mission=save_mission)
        else:
            post_travel(out=my_town, where=name_max_city)

    if my_town in castles_island and name_max_city in castles:
        if my_town == 'HarbourTwo':
            if silver_count < 800:
                complete_mission(current_castle=name_max_city, cog_plata=True)
            post_travel(out='HarbourTwo', where='HarbourOne', how='cog')
        else:
            post_travel(out=my_town, where='HarbourTwo')

    if my_town in castles and name_max_city in castles_island:
        if my_town == 'HarbourOne':
            if silver_count < 800:
                complete_mission(current_castle=name_max_city, cog_plata=True)
            post_travel(out='HarbourOne', where='HarbourTwo', how='cog')
        else:
            post_travel(out=my_town, where='HarbourOne')


if __name__ == "__main__":
    queue = multiprocessing.Queue()
    logging_process = multiprocessing.Process(target=logger_process, args=(queue,))
    logging_process.start()
    setup_logging(queue)  # Настраиваем логирование с использованием очереди
    account_verification()

    while True:
        try:
            keys_search()
        except ValueError as e:
            p_log(f"Ошибка: {e}")
            break
