import time
import multiprocessing
from bs4 import BeautifulSoup

from group import go_group
from logs.logger_process import logger_process
from logs.logs import p_log, setup_logging
from module.all_function import get_config_value, time_sleep_main, wait_until, format_time, time_sleep
from module.data_pars import heals
from module.game_function import check_progressbar, contribute_to_treasury, use_potion, post_travel, buy_ring, \
    get_reward, work, move_item, register_joust
from module.http_requests import post_request, make_request
from setting import start_game
from sliv import set_initial_gold, reduce_experience, online_tracking_only

treasury_url = 'https://s32-ru.battleknight.gameforge.com/treasury'
mission_url = 'https://s32-ru.battleknight.gameforge.com/world/location'
deposit_url = 'https://s32-ru.battleknight.gameforge.com/treasury/deposit'
world_url = 'https://s32-ru.battleknight.gameforge.com/world'
work_url = 'https://s32-ru.battleknight.gameforge.com:443/market/work'
travel_url = 'https://s32-ru.battleknight.gameforge.com:443/world/startTravel'
point_url = 'https://s32-ru.battleknight.gameforge.com/user/getPotionBar'
user_url = 'https://s32-ru.battleknight.gameforge.com/user/'


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


def attack_mission(url=mission_url, game_mode=4, mission_name='DragonLair'):
    response = make_request(url)
    time.sleep(1)
    time_sleep(check_progressbar(response))  # проверка состояния рыцаря
    time.sleep(1)
    while game_mode:
        # break_outer = False
        response = make_request(url)
        time.sleep(1)

        if heals(response) < 20:
            p_log("Слишком мало HP")
            use_potion()
            response = make_request(url)

        soup = BeautifulSoup(response.content, 'html.parser')
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
        if not game_mode:
            contribute_to_treasury()
        time_sleep(check_progressbar())


# ______________________________________________________________________________________________


# ___________________________________________________________________________________________


# __________________________________________________________________________________________________

# def fehan():
#     count_work = 2
#     while True:
#         time_sleep(check_progressbar())  # проверка состояния
#         attack_mission(mission_name='Laguna')
#         p_log("Rabota osnovnoj programmy")
#         # if count_work % 3 == 0:
#         #     work()
#         #     get_reward()
#         # elif (count_work + 2) % 3 == 0:
#         #     p_log("Sidim v Fehan 7 chasov...")
#         #     if get_config_value("attack"):
#         #         set_initial_gold()
#         #         run_process_for_hours(reduce_experience, 7, "reduce_experience")
#         #     else:
#         #         time_sleep(7 * 60 * 60 + 900 + get_config_value("correct_time"))
#         # else:
#         #     p_log("Sidim v Fehan 7 chasov...")
#         #     if get_config_value("attack"):
#         #         set_initial_gold()
#         #         run_process_for_hours(online_tracking_only, 7, "online_tracking_only")
#         #     else:
#         #         time_sleep(7 * 60 * 60 + 900 + get_config_value("correct_time"))
#         if count_work % 3 == 0:
#             work()
#             get_reward()
#         else:
#             process_function = reduce_experience if (count_work + 2) % 3 == 0 and get_config_value("reduce_experience") else online_tracking_only
#             process_name = "reduce_experience" if (count_work + 2) % 3 == 0 and get_config_value("reduce_experience") else "online_tracking_only"
#             common_actions(process_function, process_name)
#         count_work += 1

def autoplay():
    count_work = 2
    while True:

        move_item(how='loot', name='ring', rand=False)  # переместить кольцо из сундука добычи
        if get_config_value("register_joust"):
            register_joust()  # регистрация на турнир

        time_sleep(check_progressbar())
        attack_mission()
        post_travel(out='GhostTown', where='CityOne', how='horse')
        p_log("Сидим в Алкране несколько часов...")
        if count_work % 3 == 0:
            work()
            get_reward()
        else:
            # вставить вызов аукционера
            process_function = reduce_experience if (count_work + 2) % 3 == 0 and get_config_value(
                "reduce_experience") else online_tracking_only
            process_name = "reduce_experience" if (count_work + 2) % 3 == 0 and get_config_value(
                "reduce_experience") else "online_tracking_only"
            common_actions(process_function, process_name)

            # создание Групповой миссии
            if (count_work + 2) % 3 == 1:
                go_group(3600)
                timer_group = check_progressbar()
                if timer_group:
                    p_log(f"Ожидание после группы {format_time(timer_group)}. Ожидаем...")
                if get_config_value("buy_ring"):
                    buy_ring()  # покупка кольца на аукционе
                time_sleep(timer_group)

        count_work += 1
        post_travel(out='CityOne', where='GhostTown', how='horse')

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
    if get_config_value("attack"):
        run_process_for_hours(process_function, 4.9, process_name)
    else:
        time_sleep(4.9 * 60 * 60 + 900 + get_config_value("correct_time"))


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
    time_sleep(900 + get_config_value("correct_time"))


if __name__ == "__main__":
    queue = multiprocessing.Queue()
    logging_process = multiprocessing.Process(target=logger_process, args=(queue,))
    logging_process.start()
    setup_logging(queue)  # Настраиваем логирование с использованием очереди

    time_sleep(wait_until("15:25"))
    autoplay()

    # Завершение дочернего процесса логирования
    queue.put(None)  # Отправляем сигнал для завершения
    logging_process.join()  # Ждем завершения дочернего процесса
