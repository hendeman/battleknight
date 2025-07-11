import time
import multiprocessing
from random import choice

from bs4 import BeautifulSoup

from group import go_group
from logs.logger_process import logger_process
from logs.logs import p_log, setup_logging
from module.all_function import get_config_value, time_sleep_main, wait_until, format_time, time_sleep, \
    get_next_time_and_index, get_random_value
from module.data_pars import heals
from module.event_function import apply_christmas_bonus
from module.game_function import check_progressbar, contribute_to_treasury, use_potion, post_travel, buy_ring, \
    get_reward, work, move_item, register_joust, my_place, main_buy_potion, use_helper, get_castle_min_time, \
    init_status_players, account_verification
from module.http_requests import post_request, make_request
from setting import start_game, start_time, auction_castles, castles_all
from sliv import set_initial_gold, reduce_experience, online_tracking_only

treasury_url = 'https://s32-ru.battleknight.gameforge.com/treasury'
mission_url = 'https://s32-ru.battleknight.gameforge.com/world/location'
deposit_url = 'https://s32-ru.battleknight.gameforge.com/treasury/deposit'
world_url = 'https://s32-ru.battleknight.gameforge.com/world'
work_url = 'https://s32-ru.battleknight.gameforge.com:443/market/work'
travel_url = 'https://s32-ru.battleknight.gameforge.com:443/world/startTravel'
point_url = 'https://s32-ru.battleknight.gameforge.com/user/getPotionBar'
user_url = 'https://s32-ru.battleknight.gameforge.com/user/'


@apply_christmas_bonus
def post_dragon(buy_rubies='', mission_name='DragonLair'):
    payload = {
        'chooseMission': mission_name,
        'missionArt': 'small',
        'missionKarma': 'Good',
        'buyRubies': buy_rubies
    }

    post_request(world_url, payload)
    p_log(f"Атака успешна, потрачено {buy_rubies if buy_rubies else '0'} рубинов")

    # time_sleep(check_progressbar())


@use_helper('fairy')
@use_helper('boar')
def attack_mission(url=mission_url, game_mode=4, mission_name='DragonLair'):
    response = make_request(url)
    time.sleep(1)
    time_sleep(check_progressbar(response))  # проверка состояния рыцаря
    time.sleep(1)
    while game_mode:
        # break_outer = False
        mission_name = choice(mission_name) if isinstance(mission_name, list) else mission_name
        response = make_request(url)
        time.sleep(1)

        if heals(response) < 20:
            p_log("Слишком мало HP")
            use_potion()
            response = make_request(url)

        soup = BeautifulSoup(response.content, 'lxml')
        search_string = f"chooseMission('small', '{mission_name}', 'Good', this)"
        a_tags = soup.find_all('a', onclick=lambda onclick: onclick and search_string in onclick)

        if a_tags:
            # Если будешь использовать перепроверь search_string для вставки в lambda
            # for a_tag in a_tags:
            #     if 'disabledSpecialBtn' in a_tag.get('class', []):
            #         buy_rubies_tags = soup.find_all('a', class_='devLarge missionBuyRubies toolTip',
            #                                         onclick=lambda onclick: onclick and (
            #                                                 f"chooseMission('large', 'DragonLair', 'Good', this, '1')" in onclick
            #                                                 or f"chooseMission('large', 'DragonLair', 'Good', this, '2')" in onclick
            #                                                 or f"chooseMission('large', 'DragonLair', 'Good', this, '3')" in onclick))
            #         if buy_rubies_tags:
            #             for buy_rubies_tag in reversed(buy_rubies_tags):
            #                 onclick_value = buy_rubies_tag.get('onclick')
            #                 p_log(onclick_value)
            #                 if onclick_value:
            #                     parts = onclick_value.split(',')
            #                     if len(parts) > 4:
            #                         fifth_argument = parts[4].strip().strip("');")
            #
            #                         post_dragon(buy_rubies=fifth_argument)
            #                         break_outer = True
            #                         break
            #             if break_outer:
            #                 break
            # else:
            #     post_dragon(mission_name=mission_name)
            post_dragon(mission_name=mission_name)
            time.sleep(1)
        else:
            p_log('Не удалось найти тег <a> с нужным атрибутом onclick.')
        game_mode -= 1
        if not game_mode and get_config_value("contribute_to_treasury"):
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

    while True:
        phase_offset = get_config_value("phase_offset")
        move_item(how='loot', name='ring', rand=False)  # переместить кольцо из сундука добычи
        if get_config_value("register_joust"):
            register_joust()  # регистрация на турнир

        time_sleep(check_progressbar())
        attack_mission(game_mode=get_config_value("game_mode"), mission_name=mission_name)

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
            work(working_hours=8, side=side)  # отправить работать
            time_sleep(8 * 60 * 60 + int(get_random_value(60, 100)))
            get_reward()  # забрать награду за работу спустя время

            # Закупка необходимым количеством баночек HP buy_potion_count
            try:
                main_buy_potion(get_config_value("buy_potion_count"))
            except Exception as er:
                p_log(f"Ошибка покупки HP: {er}")

        elif (count_work + 2) % 3 == phase_offset:  # phase_offset 0 для первой фазы, 1 - для второй

            if get_config_value(key="online_track"):
                init_status_players()  # Обновление battle.json

            p_log(f"Значение count_work={count_work}", level="debug")
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
                go_group(3600)
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


def wrapper_function(func1, func2, process_name):
    try:
        func1()  # Запускаем первую функцию
    except Exception as e:
        p_log(f"Исключение в {func1}:", is_error=True)  # Логируем исключение с полным traceback
    try:
        func2()  # Запускаем вторую функцию
    except Exception as e:
        p_log(f"Исключение в {func2}:", is_error=True)  # Логируем исключение с полным traceback


def common_actions(process_function, process_name):
    function_duration = get_config_value("function_duration")  # продолжительность работы цикла в часах
    if get_config_value("attack"):
        run_process_for_hours(target_function=process_function, hours=function_duration, process_name=process_name)
    else:
        time_sleep(function_duration * 60 * 60 + 650 + get_config_value("correct_time"))


def run_process_for_hours(target_function, hours, process_name):
    p_log(f"Запуск {process_name} процесса...")
    process = multiprocessing.Process(target=wrapper_function, args=(set_initial_gold, target_function, process_name))
    process.start()
    p_log(f"Ожидание {hours} часов... Работает {process_name} функция")
    time_sleep_main(hours * 60 * 60)  # Ожидание в часах
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
        'not_event': {'town': 'GhostTown', 'mission_name': 'DragonLair', 'side': 'good'},
        'easter': {'town': 'TradingPostOne', 'mission_name': 'EgghatchGrotto', 'side': 'neutral'},
        'fehan': {'town': 'FogIsland', 'mission_name': ['Laguna', 'Tidesbeach', 'Fogforest'], 'side': 'good'}
    }

    autoplay(**event_list.get(get_config_value("event")))

    # Завершение дочернего процесса логирования
    queue.put(None)  # Отправляем сигнал для завершения
    logging_process.join()  # Ждем завершения дочернего процесса
