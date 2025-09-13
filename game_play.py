import time
import multiprocessing
from random import choice


from logs.logger_process import logger_process
from logs.logs import p_log, setup_logging
from module.all_function import get_config_value, time_sleep_main, wait_until, format_time, time_sleep, \
    get_next_time_and_index, get_random_value
from module.cli import arg_parser
from module.data_pars import heals
from module.game_function import check_progressbar, contribute_to_treasury, use_potion, post_travel, buy_ring, \
    get_reward, work, move_item, register_joust, my_place, main_buy_potion, use_helper, get_castle_min_time, \
    init_status_players, account_verification, check_treasury_timers, reduce_experience, online_tracking_only, \
    set_initial_gold, click, ClickResult
from module.group import go_group
from module.http_requests import make_request
from setting import start_game, start_time, auction_castles, castles_all

treasury_url = 'https://s32-ru.battleknight.gameforge.com/treasury'
mission_url = 'https://s32-ru.battleknight.gameforge.com/world/location'
deposit_url = 'https://s32-ru.battleknight.gameforge.com/treasury/deposit'
world_url = 'https://s32-ru.battleknight.gameforge.com/world'
work_url = 'https://s32-ru.battleknight.gameforge.com:443/market/work'
travel_url = 'https://s32-ru.battleknight.gameforge.com:443/world/startTravel'
point_url = 'https://s32-ru.battleknight.gameforge.com/user/getPotionBar'
user_url = 'https://s32-ru.battleknight.gameforge.com/user/'


@use_helper("comp_mission")
@use_helper("horse_mission")
def attack_mission(mission_name, mission_duration, find_karma, url=mission_url, game_mode=4):
    response = make_request(url)
    time.sleep(1)
    time_sleep(check_progressbar(response))  # проверка состояния рыцаря
    time.sleep(1)
    while game_mode:
        # break_outer = False
        mission_name = choice(mission_name) if isinstance(mission_name, list) else mission_name
        time.sleep(1)

        if heals(response) < 20:
            p_log("Слишком мало HP")
            use_potion()
            response = make_request(url)

        result = click(mission_duration, mission_name, find_karma)
        if result == ClickResult.NOT_MISSION:
            p_log(f"Свободных миссий больше нет.")
            break

        game_mode -= 1
        if not game_mode and get_config_value("contribute_to_treasury") and not check_treasury_timers():
            contribute_to_treasury()
        time_sleep(check_progressbar())


def autoplay(town, mission_name, side):
    # __________________________ Проверить статус персонажа и переместиться в Талфур _______________________
    time_sleep(check_progressbar())
    place, my_town = my_place()
    p_log(f"Я нахожусь в {place}")
    if my_town != town:
        if town == 'FogIsland':
            post_travel(out=my_town, where='CoastalFortressOne')
            my_town = 'CoastalFortressOne'
            post_travel(out=my_town, where=town, how='fogBoat')
        else:
            post_travel(out=my_town, where=town)

    count_work, next_time = get_next_time_and_index(start_time)
    time_sleep(wait_until(next_time))
    game_param = [
        get_config_value("mission_duration"),
        get_config_value("working_karma").capitalize()
    ]

    while True:
        phase_offset = get_config_value("phase_offset")
        p_log(f"phase_offset={phase_offset}, count_work={count_work}", level='debug')
        move_item(how='loot', name='ring', rand=False)  # переместить кольцо из сундука добычи
        if get_config_value("register_joust"):
            register_joust()  # регистрация на турнир

        time_sleep(check_progressbar())
        attack_mission(mission_name, *game_param, game_mode=get_config_value("game_mode"))

        # Если в городе нет аукциона, то едем в ближайший
        place, my_town = my_place()
        p_log(f"Я нахожусь в {place}")
        if my_town not in auction_castles and my_town != 'FogIsland':
            my_town = get_castle_min_time()
            post_travel(out=town, where=my_town)

            p_log(f"Сидим в {castles_all.get(my_town)} несколько часов...")

        if count_work % 3 == 0:
            if get_config_value("buy_ring"):
                buy_ring()  # покупка кольца на аукционе

            working_hours = get_config_value("working_hours")
            work(working_hours=working_hours, side=side)  # отправить работать

            use_helper("comp_tournament", restore=False, direct_call=True)

            time_sleep(working_hours * 60 * 60 + int(get_random_value(60, 100)))
            get_reward()  # забрать награду за работу спустя время

            use_helper("comp_fight", restore=False, direct_call=True)

            # Закупка необходимым количеством баночек HP buy_potion_count
            try:
                main_buy_potion(get_config_value("buy_potion_count"))
            except Exception as er:
                p_log(f"Ошибка покупки HP: {er}")

        elif (count_work + 2) % 3 == phase_offset:  # phase_offset 0 для первой фазы, 1 - для второй

            if get_config_value(key="online_track"):
                init_status_players()  # Обновление battle.json

            if get_config_value("reduce_experience"):
                common_actions(reduce_experience, "reduce_experience")
            else:
                common_actions(online_tracking_only, "online_tracking_only")
        else:
            if get_config_value("double_reduce_experience"):
                common_actions(reduce_experience, "reduce_experience")
            else:
                common_actions(online_tracking_only, "online_tracking_only")

            # создание Групповой миссии
            if (count_work + 2) % 3 == 1 - phase_offset:  # 1 - phase_offset 0 для первой фазы, 1 - для второй
                go_group()
                timer_group = check_progressbar()
                if timer_group:
                    p_log(f"Ожидание после группы {format_time(timer_group)}. Ожидаем...")
                if get_config_value("buy_ring"):
                    buy_ring()  # покупка кольца на аукционе
                time_sleep(timer_group)
        time_sleep(check_progressbar())
        count_work += 1

        # вернутся обратно в город
        place, my_town = my_place()
        p_log(f"Я нахожусь в {place}")
        if my_town != town:
            post_travel(out=my_town, where=town)

        # синхронизация общей программы
        if (count_work + 2) % 3 == 0:
            time_begin = wait_until(start_game)
            if time_begin < 36000:
                p_log(f"До начала следующего цикла {format_time(time_begin)}. Ожидаем...")
                time_sleep(time_begin)
            else:
                p_log("Цикл получился более 24 часов. Уменьшите время выполнения промежуточным программ")


def wrapper_function(func1, func2):
    try:
        func1()  # Запускаем первую функцию
    except Exception as er:
        p_log(f"Исключение в {func1}: {er}", is_error=True)  # Логируем исключение с полным traceback
    try:
        func2()  # Запускаем вторую функцию
    except Exception as er:
        p_log(f"Исключение в {func2}: {er}", is_error=True)  # Логируем исключение с полным traceback


def common_actions(process_function, process_name):
    function_duration = get_config_value("function_duration")  # продолжительность работы цикла в часах
    if get_config_value("attack"):
        run_process_for_hours(target_function=process_function, hours=function_duration, process_name=process_name)
    else:
        time_sleep(function_duration * 60 * 60 + 650 + get_config_value("correct_time"))


def run_process_for_hours(target_function, hours, process_name):
    p_log(f"Запуск {process_name} процесса...")
    process = multiprocessing.Process(target=wrapper_function, args=(set_initial_gold, target_function,))
    process.start()
    p_log(f"Ожидание {hours} часов... Работает {process_name} функция")
    time_sleep_main(hours * 60 * 60, name=process_name)  # Ожидание в часах
    p_log(f"Остановка {process_name} процесса...")
    process.terminate()
    process.join()
    p_log("Дополнительное ожидание")
    time_sleep_main(650 + get_config_value("correct_time"), interval=300)


if __name__ == "__main__":
    queue = multiprocessing.Queue()
    logging_process = multiprocessing.Process(target=logger_process, args=(queue,))
    logging_process.start()
    setup_logging(queue)  # Настраиваем логирование с использованием очереди
    account_verification()

    event_list = {
        'not_event': {'town': get_config_value("town"),
                      'mission_name': get_config_value("mission_name"),
                      'side': get_config_value("working_karma")},
        'easter': {'town': 'TradingPostOne',
                   'mission_name': 'EgghatchGrotto',
                   'side': 'neutral'},
        'fehan': {'town': 'FogIsland',
                  'mission_name': ['Laguna', 'Tidesbeach', 'Fogforest'],
                  'side': get_config_value("working_karma")}
    }
    parser = arg_parser()
    args = parser.parse_args()
    if args.fehan:
        p_log(f"Активирован мод Остров Фехан")
        autoplay(**event_list.get(args.fehan))
    if args.easter:
        p_log(f"Активирован мод Пасхальный")
        autoplay(**event_list.get(args.easter))
    else:
        autoplay(**event_list.get('not_event'))
    # Завершение дочернего процесса логирования
    queue.put(None)  # Отправляем сигнал для завершения
    logging_process.join()  # Ждем завершения дочернего процесса
