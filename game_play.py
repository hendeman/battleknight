import time
import multiprocessing
from bs4 import BeautifulSoup
from tqdm import tqdm


from logs.logs import p_log
from module.all_function import get_random_value, get_config_value, time_sleep_main, wait_until, no_cache, \
    get_name_mount, format_time
from module.data_pars import heals, get_status_horse
from module.http_requests import post_request, make_request
from setting import castles_all, status_list, CURRENT_TAX, status_list_eng, mount_list, start_game
from sliv import set_initial_gold, reduce_experience, online_tracking_only

treasury_url = 'https://s32-ru.battleknight.gameforge.com/treasury'
mission_url = 'https://s32-ru.battleknight.gameforge.com/world/location'
deposit_url = 'https://s32-ru.battleknight.gameforge.com/treasury/deposit'
world_url = 'https://s32-ru.battleknight.gameforge.com/world'
work_url = 'https://s32-ru.battleknight.gameforge.com:443/market/work'
travel_url = 'https://s32-ru.battleknight.gameforge.com:443/world/startTravel'
point_url = 'https://s32-ru.battleknight.gameforge.com/user/getPotionBar'
user_url = 'https://s32-ru.battleknight.gameforge.com/user/'


def time_sleep(seconds):
    if seconds:
        for i in tqdm(range(seconds), desc="Ostalos vremeni", unit="sec"):
            time.sleep(1)


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


def ride_pegasus(func):
    def wrapper(*args, **kwargs):
        id_horse = None
        id_pegas = mount_list['pegas']
        response = make_request(user_url)
        horse = get_status_horse(response)
        if horse and horse != id_pegas:
            id_horse = horse
            resp = make_request(
                f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/placeItem/?noCache={no_cache()}&id"
                f"={id_horse}&inventory=5&type=normal")
            if resp.json()['result']:
                p_log(f"Ездовое животное {get_name_mount(id_horse)} снято")
        if not id_horse and horse != id_pegas:
            p_log("Никакая лошадь не надета")
            id_horse = mount_list['bear']

        time_sleep(2)
        if horse != id_pegas:
            resp = make_request(f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/wearItem/?noCache={no_cache()}"
                                f"&id={id_pegas}&type=normal&invID=5&loc=character")
            if resp.json()['result']:
                p_log(f"{get_name_mount(id_pegas)} надет")

        func(*args, **kwargs)

        resp = make_request(f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/placeItem/?noCache={no_cache()}&id"
                            f"={id_pegas}&inventory=5&type=normal")
        if resp.json()['result']:
            p_log(f"{get_name_mount(id_pegas)} снят")

        time_sleep(2)
        resp = make_request(f"https://s32-ru.battleknight.gameforge.com/ajax/ajax/wearItem/?noCache={no_cache()}"
                            f"&id={id_horse}&type=normal&invID=5&loc=character")
        if resp.json()['result']:
            p_log(f"Ездовое животное {get_name_mount(id_horse)} надето")

    return wrapper


def print_status(from_town, where_town, how, tt):
    p_log(
        f"{'Едем' if how == 'horse' else 'Плывем'} из {castles_all[from_town]} в {castles_all[where_town]}. Ожидание {tt}")


@ride_pegasus
def post_travel(out='', where='', how='horse'):
    make_request(travel_url)
    payload = {
        'travelwhere': f'{where}',
        'travelhow': f'{how}',
        'travelpremium': 0
    }
    p_log(payload, level='debug')
    responce_redirect = post_request(travel_url, payload)  # ответ редирект
    timer_travel = check_progressbar(responce_redirect)
    if not timer_travel:
        p_log("Рыцарь не уехал в другой город!", level='warning')
    else:
        print_status(out, where, how, seconds_to_hhmmss(timer_travel))

    time_sleep(check_progressbar(responce_redirect))


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


# _____________________ Проверка состояния check_progressbar, проверка на работу progressbar_ends
def check_progressbar(resp=None):
    if resp is None:
        resp = make_request(mission_url)
    # heals(resp)
    soup = BeautifulSoup(resp.text, 'lxml')
    element = soup.find('h1').text.strip()
    p_log("Проверка состояния")

    if element in status_list:
        index = status_list.index(element)
        element_eng = status_list_eng[index]
        p_log(f"lupatik status <{element}>")
        return progressbar_ends(soup)
    p_log("lupatik свободен")


def check_treasury_timers():
    soup = BeautifulSoup(make_request(treasury_url).text, 'lxml')
    element = soup.find(class_='scrollLongTall')

    # Проверяем наличие класса hidden. Если есть hidden, то доступна казна
    if element and 'hidden' not in element.get('class', []):
        p_log(f"Элемент с классом 'scrollLongTall' имеет класс 'hidden': {element.text.strip().split()[0]}")
        return progressbar_ends(soup)


def progressbar_ends(soup):
    try:
        timer = soup.find(id="progressbarEnds").text.strip()
        hours, minutes, seconds = map(int, timer.split(':'))
        total_seconds = hours * 3600 + minutes * 60 + seconds + 2
    except AttributeError:
        if soup.find('h1').text.strip() == 'Работа':
            get_reward()
        total_seconds = 0

    return total_seconds


def seconds_to_hhmmss(seconds):
    if seconds is None:
        return None
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"


# ______________________________________________________________________________________________

# ____________Отправить рыцаря на работу work и получить награду за работу get_reward___________
def work():
    payload = {
        'hours': '6',
        'side': 'good'
    }
    make_request(work_url)
    time.sleep(1)
    post_request(work_url, payload)
    p_log("Работаем 6 часов...")
    time_sleep(21700)


def get_reward():
    make_request(work_url)
    payload = {'paycheck': 'encash'}

    post_request(work_url, payload)
    p_log(f"Награда за работу принята")


# ________________________________________________________________________________________________


# ____________________________ Скинуть золото в казну ____________________________________
def contribute_to_treasury():
    gold_all = put_gold(status="before")
    payload = {'silvertoDeposit': int(gold_all * CURRENT_TAX) - 100}
    p_log(payload, level='debug')
    post_request(deposit_url, payload)
    put_gold(status="after")


def put_gold(status="before"):
    soup = BeautifulSoup(make_request(treasury_url).text, 'lxml')
    gold_count_element = int(soup.find(id="silverCount").text.split()[0])
    p_log(
        f"Количество золота на руках: {gold_count_element}" if status == "before"
        else f"Осталось золота после казны: {gold_count_element}")
    return gold_count_element


# ___________________________________________________________________________________________

# __________ Использовать зелье use_potion, получить данные о зельях_________________________
def use_potion():
    try:
        last_item_id, last_item_value = get_potion_bar()
        p_log(f"Будет использовано зелье на {last_item_value} HP")
        time.sleep(get_random_value())
        use_url = (
            f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/usePotion?noCache={no_cache()}&id={last_item_id}'
            '&merchant=false&table=user')
        make_request(use_url)
        time.sleep(get_random_value())
        # Получить новый список из зельев
        get_potion_bar()
    except:
        p_log("Ошибка в получении банок ХП. Отдыхаем 10 минут")
        time_sleep(600)


def get_potion_bar():
    payload = {
        'noCache': f'{int(time.time() * 1000)}'
    }
    data = post_request(point_url, payload).json()
    result = ', '.join(f"{item['item_pic']} - {str(item['count'])}" for item in data.values())
    p_log(result)
    sorted_keys = sorted(data.keys(), key=int)
    sorted_items = [data[key] for key in sorted_keys]
    last_item_id, last_item_value = sorted_items[-1]['item_id'], sorted_items[-1]['item_value']
    return last_item_id, last_item_value


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
    count_work = 3
    while True:
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
            # вставить вызов группы, только уменьшить время выполнения online_tracking_only
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
        run_process_for_hours(process_function, 6.5, process_name)
    else:
        time_sleep(6.5 * 60 * 60 + 900 + get_config_value("correct_time"))


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
    time_sleep(wait_until("23:10"))
    autoplay()
