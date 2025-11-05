from bs4 import BeautifulSoup

from game_play import run_process_for_hours
from logs.logging_config import setup_logging_system, cleanup_logging_system
from logs.logs import p_log
from module.game_function import post_travel, my_place, check_hit_point, hide_silver, check_status_mission, \
    get_all_items, check_mission, get_group_castles, post_dragon, check_time_sleep, is_time_between, move_item, \
    get_silver, \
    check_progressbar, go_auction, buy_ring, account_verification, reduce_experience, online_tracking_only, \
    find_mission, get_zone, select_castle_by_top_count
from module.group import go_group
from module.http_requests import make_request
from module.all_function import time_sleep, format_time, get_save_castle, clear_save_castle, write_save_castle, \
    get_config_value, time_sleep_main, load_json_file
from setting import castles_all, url_world, url_map, auction_castles

queue = None

ZONE_GATEWAYS = load_json_file('configs', 'zone_gateways.json')
MACRO_ZONE = {
    'brent': 'continent',
    'alcran': 'continent',
    'hatwig': 'continent',
    'endaline': 'continent',
    'continent': 'continent',
    'island': 'island'
}


# ___________________ Выполнить миссию. Флаг cog_plata=True значит миссия для переправы __________


def complete_mission(current_castle, length_mission, save_mission=None, cog_plata=False):
    response = make_request(url_world)
    soup = BeautifulSoup(response.content, 'lxml')
    name_mission = find_mission(soup, length_mission, all_mission=True)
    if save_mission:
        element = name_mission.index(save_mission)
        name_mission = name_mission[element:]
    flag = False
    flag_cog = False

    def process_mission_with_keys(miss, buy_rubies=''):
        """
        Общая функция для обработки миссий с проверкой ключей.

        :param miss: Название миссии.
        :param buy_rubies: Параметр для функции check_mission (может быть None или '1').
        :return: Кортеж (остановить_цикл, флаг_ключа).
        """
        p_log(f"Будет произведена попытка пройти {miss} миссию")
        differences = check_mission(name_mission=miss, buy_rubies=buy_rubies)
        if not differences:
            p_log(f"Миссия {miss} не открыла ключ. Идем на другую")
            return True, False  # Прерываем цикл, так как миссия не открыла ключ

        current_dict_key = get_group_castles(get_all_items("key"))

        if current_castle in current_dict_key or (get_config_value("fix_bad_keys") and current_castle == 'VillageOne'):
            p_log(f"Миссия {miss} открыла ключ. Миссия будет выполнена повторно")
            p_log(f"В данной локации осталось ещё {current_dict_key.get(current_castle, {}).get('count', 0)} ключей")
            write_save_castle(current_castle, miss)
            return False, False

        # Если дошли до этой точки, значит current_castle НЕ в словаре и специальное условие не сработало
        p_log(f"В городе {current_castle} все ключи открыты")
        return True, True

    p_log(f"В {castles_all.get(current_castle)} имеются следующие миссии {name_mission}")
    for mission in name_mission:
        while True:
            gold_limit = get_config_value(key='gold_limit')

            # ____________________________ Ночной перерыв _________________________________
            check_time_sleep(start_hour='00:00', end_hour='02:00', sleep_hour='07:00')
            # _______________________ Время для групповой миссии __________________________
            check_time_sleep(start_hour='19:20', end_hour='21:29', sleep_hour='21:30')

            if is_time_between(start_hour='21:29', end_hour='21:35'):
                go_group()
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
                            run_process_for_hours(reduce_experience, 1.75,
                                                  'reduce_experience',
                                                  log_queue=queue)
                        else:
                            run_process_for_hours(online_tracking_only, 1.75,
                                                  'online_tracking_only',
                                                  log_queue=queue)
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
            if silver_count >= 140 and get_config_value("buy_key"):
                move_item(how='buy')  # купить ключ
            move_item(how='loot')  # переместить ключи из сундука добычи
        except Exception as er:
            p_log(f"Ошибка выполнения move_item: {er}", level='warning')


def get_directions(macro_route_key, my_town, silver_count, length_mission, name_max_city=None):
    gateway = ZONE_GATEWAYS[macro_route_key]
    from_gate = gateway['from_gate']
    to_gate = gateway['to_gate']
    transport = gateway.get('transport')

    if my_town == from_gate:
        if silver_count < 800:
            complete_mission(current_castle=name_max_city, length_mission=length_mission, cog_plata=True)
        post_travel(out=from_gate, where=to_gate, how=transport)
    else:
        post_travel(out=my_town, where=from_gate)


def keys_search():
    while True:
        length_mission = get_config_value("mission_duration")
        time_sleep(check_progressbar())  # проверить статус
        # check_time_sleep(start_hour='00:00', end_hour='02:00', sleep_hour='07:00')
        place, my_town = my_place()  # Джаро, VillageFour
        p_log(f"Я нахожусь в {place}")
        all_keys = get_all_items("key")
        group_castles = get_group_castles(all_keys)

        response = make_request(url_map)
        soup = BeautifulSoup(response.text, 'lxml')
        silver_count = int(soup.find(id='silverCount').text)
        halloween_tag = soup.find('div', id='paymentPromo')

        save_castle = get_save_castle()  # проверяем, если замок в файле
        if save_castle:
            name_max_city, save_mission = next(iter(save_castle.items()))
        else:
            try:
                name_max_city = select_castle_by_top_count(group_castles, halloween_tag)
                save_mission = None
            except ValueError:
                p_log(group_castles, level="debug")
                raise ValueError("Все ключи открыты")

        if not name_max_city:
            raise f"Нет доступных ключей"
        p_log(f"Максимальное количество ключей находится в "
              f"{castles_all[name_max_city]}, {group_castles.get(name_max_city, {}).get('count', 0)} ключей")

        my_zone = get_zone(my_town)
        dragon_zone = get_zone(name_max_city)

        # Случай 1: один и тот же город
        if my_zone == dragon_zone:
            if my_town == name_max_city:
                p_log(f"Вы в городе {castles_all[name_max_city]} с максимальным количеством ключей!")
                check_hit_point()
                complete_mission(current_castle=name_max_city,
                                 length_mission=length_mission,
                                 save_mission=save_mission)
            else:
                post_travel(out=my_town, where=name_max_city)
            continue

        # Случай 2: явно заданный маршрут (например, brent <-> alcran)
        route_key = f"{my_zone}->{dragon_zone}"
        if route_key in ZONE_GATEWAYS and ZONE_GATEWAYS[route_key].get('transport') == "longBoat":
            get_directions(route_key, my_town, silver_count, length_mission, name_max_city)
            continue

        # Случай 3: обобщённые макрозоны (continent <-> island)
        my_macro = MACRO_ZONE[my_zone]
        dragon_macro = MACRO_ZONE[dragon_zone]

        if my_macro == dragon_macro:
            # В одной макрозоне, но нет явного маршрута → прямой переход
            post_travel(out=my_town, where=name_max_city)
        else:
            # Разные макрозоны → используем обобщённый маршрут
            macro_route_key = f"{my_macro}->{dragon_macro}"
            if macro_route_key not in ZONE_GATEWAYS:
                raise RuntimeError(f"Нет маршрута из {my_macro} в {dragon_macro}")

            get_directions(macro_route_key, my_town, silver_count, length_mission, name_max_city)


if __name__ == "__main__":
    queue, logging_process, translate = setup_logging_system()
    account_verification()

    keys_search()

    cleanup_logging_system(queue, logging_process, translate)
