import multiprocessing

from functools import partial

from bs4 import BeautifulSoup

from logs.logging_config import setup_logging_system, cleanup_logging_system
from logs.logs import p_log, setup_logging
from module.data_pars import get_point_mission
from module.ruby_manager import ruby_manager
from module.all_function import time_sleep, wait_until, format_time, time_sleep_main, get_config_value, \
    load_json_file, kill_process_hierarchy
from module.cli import arg_parser
from module.game_function import check_timer, post_dragon, check_hit_point, post_travel, my_place, check_time_sleep, \
    post_healer, check_progressbar, move_item, check_treasury_timers, buy_ring, contribute_to_treasury, get_silver, \
    go_auction, account_verification, online_tracking_only, find_mission, get_zone, check_status_mission
from module.group import go_group
from module.http_requests import make_request
from setting import castles_all, url_world, url_map, url_zany_healer, event_healer_potions, auction_castles

event_list = {
    'dragon': {'icon': 'DragonIcon', 'name': 'DragonEventGreatDragon'},
    'healer': {'icon': 'ZanyHealerIcon', 'name': ''}
}
EVENT_NAME = None
ZONE_GATEWAYS = load_json_file('configs', 'zone_gateways.json')
MACRO_ZONE = {
    'brent': 'continent',
    'alcran': 'continent',
    'hatwig': 'continent',
    'endaline': 'continent',
    'continent': 'continent',
    'island': 'island'
}


def complete_mission(soup, length_mission, name_mission, my_town, cog_plata=False):
    name_mission, a_tags = find_mission(soup, length_mission, name_mission)
    p_log(f"name_mission={name_mission}", level='debug')
    while True:
        if 'disabledSpecialBtn' in a_tags[0].get('class', []):
            p_log("Миссий нет. Ждем час...")

            # пока миссий нету, запускаем процесс атак на коровок
            hours = 1
            online_tracking = partial(online_tracking_only)
            process_online_tracking = multiprocessing.Process(target=wrapper_function,
                                                              args=(online_tracking,))
            process_online_tracking.start()
            p_log(f"Ожидание {hours} часов... Работает online_tracking функция")
            p_log(f"processPID={process_online_tracking.pid}", level='debug')
            time_sleep_main(hours * 60 * 60)  # Ожидание в часах
            p_log(f"Остановка online_tracking процесса...")
            process_online_tracking.terminate()
            process_online_tracking.join()
            p_log("Дополнительное ожидание")
            time_sleep_main(650 + get_config_value("correct_time"), interval=300)
            break
            # a_tags = check_status_mission(name_mission)
        else:
            p_log("Есть доступные миссии")
            check_hit_point()  # проверка количества здоровья

            if name_mission == "DragonEventGreatDragon":
                dragon_bar = soup.find('div', id='dragonLiveBar')['style']
                p_log(f"У дракона осталось {dragon_bar.split()[1]} здоровья")

            post_dragon(name_mission=name_mission)

            a_tags = check_status_mission(name_mission)

            silver_count = int(soup.find(id='silverCount').text)
            p_log(f"Свободные очки миссий: {get_point_mission(soup)}")

            # Купить кольцо на аукционе, либо положить в казну
            if name_mission == "DragonEventGreatDragon" and silver_count > get_config_value("gold_limit"):
                if get_config_value("buy_ring"):
                    not_auction_timer = any([check_time_sleep(start_hour='10:45', end_hour='12:45', sleep_hour=None),
                                             check_time_sleep(start_hour='22:45', end_hour='23:59', sleep_hour=None)])
                    if my_town not in auction_castles and not not_auction_timer:
                        go_auction(out=my_town, going_back=False, tariff_travel=800)
                    else:
                        buy_ring(tariff_travel=800)  # покупка кольца на аукционе
                    silver_count = get_silver()  # обновить количество серебра
                if silver_count > get_config_value("gold_limit") and get_config_value(
                        "contribute_to_treasury") and not check_treasury_timers():
                    silver_count = contribute_to_treasury()

            if not cog_plata and name_mission != "DragonEventGreatDragon":
                num_point = get_config_value(key='event_healer_potion')
                price_potion = event_healer_potions[num_point]['price']
                if silver_count >= price_potion:
                    make_request(url_zany_healer)
                    post_healer(num_point)
                    break
                p_log(f"Необходимо {price_potion} серебра. На руках {silver_count}")
            else:
                if silver_count >= 800:
                    break
                p_log(f"Необходимо 800 серебра. На руках {silver_count}")


def process_page(event, length_mission, name_mission, my_town):
    karma = get_config_value("working_karma").capitalize()
    break_outer = False
    response = make_request(url_world)
    soup = BeautifulSoup(response.content, 'lxml')
    a_tags = []

    if event == 'dragon':
        st = f"chooseMission('{length_mission}', '{name_mission}', '{karma}', this)"
        a_tags = soup.find_all('a', onclick=lambda onclick: onclick and st in onclick)
        p_log(a_tags, level='debug')

    if event == 'healer':
        silver_count = int(soup.find(id='silverCount').text)
        num_point = get_config_value(key='event_healer_potion')
        price_potion = event_healer_potions[num_point]['price']
        if silver_count >= event_healer_potions[num_point]['price']:
            make_request(url_zany_healer)
            post_healer(num_point)
        else:
            p_log(f"Необходимо {price_potion} серебра. На руках {silver_count}")
            name_mission, a_tags = find_mission(soup, length_mission, name_mission)

    if a_tags:
        for a_tag in a_tags:
            rubies = ruby_manager.total_used < ruby_manager.total_limit and ruby_manager.should_use_rubies()
            if rubies and 'disabledSpecialBtn' in a_tag.get('class', []):
                onclick_pattern_1 = f"chooseMission('{length_mission}', '{name_mission}', '{karma}', this, '1')"
                onclick_pattern_2 = f"chooseMission('{length_mission}', '{name_mission}', '{karma}', this, '2')"
                onclick_pattern_3 = f"chooseMission('{length_mission}', '{name_mission}', '{karma}', this, '3')"
                buy_rubies_tags = soup.find_all('a', class_='devLarge missionBuyRubies toolTip',
                                                onclick=lambda onclick: onclick and (
                                                        onclick_pattern_1 in onclick
                                                        or onclick_pattern_2 in onclick
                                                        or onclick_pattern_3 in onclick))
                if buy_rubies_tags:
                    for buy_rubies_tag in reversed(buy_rubies_tags):
                        onclick_value = buy_rubies_tag.get('onclick')
                        p_log(onclick_value)
                        if onclick_value:
                            parts = onclick_value.split(',')
                            if len(parts) > 4:
                                fifth_argument = parts[4].strip().strip("');")

                                post_dragon(name_mission=name_mission, buy_rubies=fifth_argument)
                                ruby_manager.mark_ruby_used()
                                p_log(
                                    f"Дневной лимит: {ruby_manager.daily_used}/{ruby_manager.daily_limit}, "
                                    f"Всего: {ruby_manager.total_used}/{ruby_manager.total_limit}")
                                break_outer = True
                                break
                    if break_outer:
                        break
        else:
            complete_mission(soup, length_mission, name_mission, my_town)

    else:
        if event == 'dragon':
            p_log('Не удалось найти тег <a> с нужным атрибутом onclick.')


def travel_mission(length_mission='small'):
    response = make_request(url_world)
    soup = BeautifulSoup(response.content, 'lxml')
    complete_mission(soup, length_mission, name_mission=None, my_town=None, cog_plata=True)


def get_directions(macro_route_key, my_town, silver_count, length_mission):
    gateway = ZONE_GATEWAYS[macro_route_key]
    from_gate = gateway['from_gate']
    to_gate = gateway['to_gate']
    transport = gateway.get('transport')

    if my_town == from_gate:
        if silver_count < 800:
            travel_mission(length_mission=length_mission)
        post_travel(out=from_gate, where=to_gate, how=transport)
    else:
        post_travel(out=my_town, where=from_gate)


def event_search(event):
    check_timer()
    while True:
        length_mission = get_config_value("mission_duration")
        check_time_sleep(start_hour='23:55', end_hour='01:45', sleep_hour='07:00')
        if event == 'dragon':
            move_item(how='loot', name='ring', rand=False)

        place, my_town = my_place()  # Джаро, VillageFour
        p_log(f"Я нахожусь в {place}")
        response = make_request(url_map)
        soup = BeautifulSoup(response.text, 'lxml')
        silver_count = int(soup.find(id='silverCount').text)
        try:
            dragon_town = soup.find(id=event_list[event]['icon']).get('class')[0]
        except AttributeError:
            raise AttributeError(f"{event} нет на карте")
        p_log(f"{event} находится в {castles_all[dragon_town]}")

        my_zone = get_zone(my_town)
        dragon_zone = get_zone(dragon_town)

        # Случай 1: один и тот же город
        if my_zone == dragon_zone:
            if my_town == dragon_town:
                p_log(f"Вы в городе с {event}!")
                check_hit_point()
                process_page(
                    event=event,
                    length_mission=length_mission,
                    name_mission=event_list[event]['name'],
                    my_town=my_town
                )
            else:
                post_travel(out=my_town, where=dragon_town)
            continue

        # Случай 2: явно заданный маршрут (например, brent <-> alcran)
        route_key = f"{my_zone}->{dragon_zone}"
        if route_key in ZONE_GATEWAYS:
            get_directions(route_key, my_town, silver_count, length_mission)
            continue

        # Случай 3: обобщённые макрозоны (continent <-> island)
        my_macro = MACRO_ZONE[my_zone]
        dragon_macro = MACRO_ZONE[dragon_zone]

        if my_macro == dragon_macro:
            # В одной макрозоне, но нет явного маршрута → прямой переход
            post_travel(out=my_town, where=dragon_town)
        else:
            # Разные макрозоны → используем обобщённый маршрут
            macro_route_key = f"{my_macro}->{dragon_macro}"
            if macro_route_key not in ZONE_GATEWAYS:
                raise RuntimeError(f"Нет маршрута из {my_macro} в {dragon_macro}")

            get_directions(macro_route_key, my_town, silver_count, length_mission)


def wrapper_function(func1):
    global queue
    setup_logging(queue=queue)
    try:
        func1()  # Запускаем первую функцию с аргументами
    except Exception as e:
        p_log(f"Исключение в {func1}: {e}", level='warning')


def autoplay(partial_event_search):
    while True:
        if not check_time_sleep(start_hour='19:51', end_hour='21:21'):
            p_log(f"Запуск {EVENT_NAME} процесса...")
            process = multiprocessing.Process(target=wrapper_function, args=(partial_event_search,))
            process.start()
            p_log(f"Процесс {EVENT_NAME} будет работать до 20:00...")
            p_log(f"processPID={process.pid}", level='debug')
            time_sleep_main(wait_until('20:00'), interval=5000, name='Healer search program. Remaining:')
            p_log(f"Остановка {EVENT_NAME} процесса...")
            kill_process_hierarchy(process.pid)
            process.join()
        check_timer()
        # Ожидание до 21:20 для синхронизации. 2 часа должно быть достаточно в большинстве случаев
        time_begin = wait_until("21:20")
        p_log(f"До начала группы осталось {format_time(time_begin)}. Ожидаем...")
        time_sleep(time_begin)
        # Создаем группу
        go_group()
        timer_group = check_progressbar()
        if timer_group:
            p_log(f"Ожидание после группы {format_time(timer_group)}. Ожидаем...")
            time_sleep(timer_group)


if __name__ == "__main__":
    queue, logging_process, translate = setup_logging_system()

    parser = arg_parser()
    args = parser.parse_args()
    if args.dragon or args.healer:  # или другое условие для лекаря
        account_verification()
        check_timer()

        if args.dragon:
            p_log(f"Активирован мод Охота на драконов")
            EVENT_NAME = 'dragon'
        else:  # args.healer
            p_log(f"Активирован мод Лекарь")
            EVENT_NAME = 'healer'

        autoplay(partial(event_search, EVENT_NAME))
    else:
        parser.print_help(filter_group='event')

    cleanup_logging_system(queue, logging_process, translate)
