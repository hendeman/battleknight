import pickle
import json
import re
import time

from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from requests import Response

from logs.logs import p_log, setup_logging
from module.all_function import current_time, time_sleep, get_config_value, format_time
from module.data_pars import pars_gold_duel
from module.game_function import buy_ring, is_time_between, check_progressbar, check_time_sleep, check_health, \
    get_silver, handle_ring_operations, get_gold_for_player, account_verification
from module.group import go_group
from module.http_requests import make_request, post_request
from setting import status_list, waiting_time, GOLD_GAMER, NICKS_GAMER, url_compare, url_duel_name, url_orden_message, \
    url_ordermail, url_error, url_nicks, world_url, url_name_json, get_name, url_group

date = datetime(2024, 9, 17, 19)


def make_attack(nick, heals_point=False):
    if check_health(heals_point=heals_point) < 10:
        return False, False
    url_fight = url_duel_name + str(nick)
    p_log(f"Попытка атаки на {nick}")
    resp = make_request(url_fight)
    status_duel = get_status(resp)

    if status_duel == 'Дуэль':
        p_log(f"Атака {nick} произведена успешно")
        return True, resp

    while status_duel in status_list:
        p_log(f"{get_name()} status: {status_duel}")
        time_sleep()
        p_log(f"Попытка атаки на {nick}")
        resp = make_request(url_fight)
        if resp.url == url_error:
            duel_stat = handle_error(nick)
            if duel_stat:
                return True, duel_stat
            return False, resp
        status_duel = get_status(resp)

        if status_duel == 'Дуэль':
            p_log(f"Атака на {nick} произведена успешно")
            return True, resp

    duel_stat = handle_error(nick)
    if duel_stat:
        return True, duel_stat
    return False, resp


def get_status(resp):
    soup = BeautifulSoup(resp.text, 'lxml')
    return soup.find('h1').text


def get_gold_duel(resp):
    soup = BeautifulSoup(resp.text, 'lxml')
    result = int(soup.find('div', class_='fightResultsInner').find_all('em')[1].text)
    fight_status = soup.find('div', class_='fightResultsInner').find_all('em')[0].text
    p_log(f"{fight_status}. Получено {result} серебра")
    return result


def check_status_group():
    resp = make_request(url_group)
    soup = BeautifulSoup(resp.text, 'lxml')
    h4_tags = soup.find_all('h4')
    # Проверяем наличие текста 'Изменить настройки группы' в списке тегов <h4>
    for tag in h4_tags:
        if 'Изменить настройки группы' in tag.get_text(strip=True):
            return True

    return False


def handle_error(nick):
    if check_status_group():
        p_log("Мы находимся в группе, отдыхаем 10 минут")
        time_sleep()
    else:
        try:
            url_fight = url_compare + str(nick)
            resp = make_request(url_fight)
            soup = BeautifulSoup(resp.text, 'lxml')
            script_texts = soup.find_all('script')
            all_script_content = ' '.join(script.string for script in script_texts if script.string)
            pattern = re.compile(r"document\.id\('devAttackBtn'\)\.store\('tip:title',\s*'([^']+)'\)")
            match = pattern.search(all_script_content)
            if match:
                extracted_text = match.group(1)
                p_log(extracted_text)
                return extracted_text
            else:
                p_log("Нет совпадений. Проверке парсинг состония дуэли")
        except Exception:
            p_log("Рыцарь недоступен, либо был атакован в течение 12 часов", level='warning')

    return False


def update_players_gold(dict_gamer, list_of_players):
    for gamer in list_of_players:
        list_of_players[gamer].setdefault('time',
                                          dict_gamer[gamer].get('time', date) if gamer in dict_gamer else date)
        list_of_players[gamer].setdefault('win_status',
                                          dict_gamer[gamer].get('win_status',
                                                                "uncertain") if gamer in dict_gamer else "uncertain")
        list_of_players[gamer].setdefault('spoil',
                                          dict_gamer[gamer].get('spoil', 0) if gamer in dict_gamer else 0)
        list_of_players[gamer]["gold"] = get_gold_for_player(gamer)

    return list_of_players


def set_initial_gold():
    with open(url_name_json, 'r', encoding='utf-8') as file:
        list_of_players = json.load(file)

        if get_config_value(key='exclude_allow_attack'):
            list_of_players = {key: value for key, value in list_of_players.items() if value.get('allow_attack')}

    try:
        with open(GOLD_GAMER, 'rb') as file_gamer:
            p_log("Сканирование добычи игроков...")
            dict_gamer = pickle.load(file_gamer)

    except FileNotFoundError:
        p_log("Файла не существует, будет создан новый", level='warning')
        dict_gamer = {}

    filtered_dct = update_players_gold(dict_gamer, list_of_players)

    # filtered_dct = {key: dict_gamer[key] for key in list_of_players}
    with open(GOLD_GAMER, 'wb') as file_gamer:
        pickle.dump(filtered_dct, file_gamer)
        p_log("Файл игроков успешно сохранен", level='debug')


def online_tracking():
    GOLD_LIMIT = get_config_value(key='gold_limit')
    with open(GOLD_GAMER, 'rb') as file_gamer:
        p_log("online_tracking", level='debug')
        dict_gamer = pickle.load(file_gamer)
        filtered_data = {key: value for key, value in dict_gamer.items() if
                         (datetime.now() - value['time']) > timedelta(hours=12)}
        if not filtered_data:
            p_log("В gamer_gold.pickle нападать не на кого")
            return False

        for gamer in sorted(filtered_data, key=lambda x: filtered_data[x]['allow_attack'], reverse=True):
            if filtered_data[gamer]['allow_attack']:
                golden_factor = get_config_value('golden_factor')
                gold = get_gold_for_player(gamer)
                gold_diff = gold - filtered_data[gamer]['gold']
                gold_diff_proc = int(gold_diff / (filtered_data[gamer]['gold_diff'] * golden_factor) * 100)
                p_log(f"{gamer} {filtered_data[gamer]['name']} накопил {gold_diff} [{gold_diff_proc}%] серебра")
            else:
                golden_factor, gold = 0, 99999999  # заглушка для "allow_attack": false
                p_log(f"Атака вне слежки на {filtered_data[gamer]['name']}")
            time_str, current_date = current_time()
            time.sleep(2)
            if gold - filtered_data[gamer]["gold"] > filtered_data[gamer]['gold_diff'] * golden_factor:
                flag, resp = make_attack(gamer, heals_point=True)
                if flag:
                    silver = get_silver()
                    if silver > GOLD_LIMIT - 500 and get_config_value("buy_ring"):
                        buy_ring()  # покупка кольца на аукционе
                    received_gold, win_status = (pars_gold_duel(resp, gold_info=True, win_status=True)
                                                 if isinstance(resp, Response)
                                                 else (0, resp)
                                                 )
                    dict_gamer[gamer]["time"] = current_date
                    dict_gamer[gamer]["win_status"] = win_status
                    dict_gamer[gamer]["spoil"] = received_gold

                    # Отправить в орден коровку
                    if win_status == f"{get_name()} выиграл" and received_gold > 100:
                        p_log(win_status)
                        p_log(f"{filtered_data[gamer]['name']} +{received_gold}")
                        if get_config_value(key='order_message'):
                            message = f"{filtered_data[gamer]['name']} +{received_gold}"
                            make_request(url_ordermail)
                            orden_message(message)
                            p_log("Отправлено сообщение в орден")

                    with open(GOLD_GAMER, 'wb') as file_gamer:
                        pickle.dump(dict_gamer, file_gamer)
                    if isinstance(resp, Response):
                        time_sleep()
                    return "sleep"
        return True


def online_tracking_only(reduce_flag=False):
    while True:
        status_sleep = online_tracking()
        if status_sleep == "sleep":
            continue
        if status_sleep and not reduce_flag:
            time_sleep()
        else:
            break


def reduce_experience(name_file=NICKS_GAMER, tracking=True):
    init_handle_ring_operations = handle_ring_operations(buy_ring(initial=True), False)

    with open(name_file, 'rb') as f:
        loaded_dict = pickle.load(f)
        sorted_dict = {k: v for k, v in sorted(loaded_dict.items(),
                                               key=lambda item: (
                                                   -item[1]['spoil'] if item[1]['spoil'] > 50 else float('inf'),
                                                   item[1]['time']
                                               ))}

        # number_of_attacks задается из config.ini - количесвто проводимых атак
        number_of_attacks = get_config_value(key="number_of_attacks")
        attack_flag = False

        for nick in sorted_dict:
            # online_track = 1 tracking active from config.ini
            if tracking and attack_flag and get_config_value(key="online_track"):
                online_tracking_only(reduce_flag=True)  # функция нахождения и атаки на играющих игроков

            time_str, current_date = current_time()
            difference_data = current_date - loaded_dict[nick]["time"]
            if int(difference_data.total_seconds() / 3600) >= 12:
                flag, resp = make_attack(nick)
                if flag:
                    received_gold = pars_gold_duel(resp, gold_info=True) if isinstance(resp, Response) else 0
                    silver = get_silver()

                    # инициализация стоимости кольца либо покупка кольца на аукционе
                    init_handle_ring_operations(silver)

                    loaded_dict[nick]["time"] = current_date
                    loaded_dict[nick]["spoil"] = received_gold
                    with open(name_file, 'wb') as f:
                        pickle.dump(loaded_dict, f)
                    if isinstance(resp, Response):
                        p_log("Ожидание 10 мин перед следующей атакой...")
                        time_sleep()
                        attack_flag = True
                    else:
                        attack_flag = False

                    number_of_attacks -= 1
                    if not number_of_attacks:
                        break
            else:
                p_log(f"{nick} не может быть атакован", level='debug')
                attack_flag = False
        # когда закончилился список из рыцаряй для слива опыта
        if tracking and get_config_value(key="online_track"):
            online_tracking_only()


def korovk_reduce_experience(name_file=NICKS_GAMER):
    def update_knight_data(loaded_dict, nick, current_date, received_gold):
        loaded_dict[nick]["time"] = current_date
        loaded_dict[nick]["spoil"] = received_gold
        with open(name_file, 'wb') as f:
            pickle.dump(loaded_dict, f)

    with open(name_file, 'rb') as f:
        loaded_dict = pickle.load(f)
        sorted_dict = {k: v for k, v in sorted(loaded_dict.items(), key=lambda item: item[1]["spoil"], reverse=True)}
        list_fail = []
        while sorted_dict or list_fail:
            for nick in list(sorted_dict.keys()):
                time_str, current_date = current_time()
                difference_data = current_date - loaded_dict[nick]["time"]
                if int(difference_data.total_seconds() / 3600) >= 12:
                    flag, resp = make_attack(nick)
                    if flag:
                        received_gold = pars_gold_duel(resp, gold_info=True)
                        update_knight_data(loaded_dict, nick, current_date, received_gold)
                        del sorted_dict[nick]

                        p_log(f"Ожидание {waiting_time} сек перед следующей атакой")
                        time_sleep()
                        if list_fail:
                            break
                        online_tracking()  # функция нахождения и атаки на играющих игроков
                    else:
                        list_fail.append(nick)
                        del sorted_dict[nick]
                        continue
                else:
                    del sorted_dict[nick]
                    continue

            flag_sleep = False
            if list_fail:
                p_log(f"Список неудачных атак: {list_fail}")
                for fail_nick in list_fail[:]:
                    flag, resp = make_attack(nick)
                    last_fail_nick = list_fail[-1]
                    if flag:
                        received_gold = pars_gold_duel(resp, gold_info=True)
                        if fail_nick == last_fail_nick:
                            flag_sleep = True

                        update_knight_data(loaded_dict, fail_nick, current_date, received_gold)
                        list_fail.remove(fail_nick)

                        p_log(f"Ожидание {waiting_time} сек перед следующей атакой")
                        time_sleep()
                if not sorted_dict and not flag_sleep:
                    time_sleep()

        p_log("Все рыцари успешно пройдены")


def change_pickle_file(name_file=GOLD_GAMER):
    with open(name_file, 'rb+') as f:
        loaded_dict = pickle.load(f)
        # delete_list = list(loaded_dict.keys())
        # for i in delete_list:
        #     if loaded_dict[i]['gold'] < 500:
        #         del loaded_dict[i]
        p_log(loaded_dict)
        loaded_dict['984811']['time'] = datetime(2024, 9, 17, 18)

        f.seek(0)  # Перемещение курсора в начало файла
        f.truncate()  # Очистка содержимого файла
        pickle.dump(loaded_dict, f)
        p_log(f"Данные успешно обновлены в файл {name_file}. Всего {len(loaded_dict)} записей")


def create_pickle_file(name_file=NICKS_GAMER):
    with open(name_file, 'rb+') as f:
        loaded_dict = pickle.load(f)
        with open(url_nicks, 'r', encoding='utf-8') as file_nicks:
            for i in file_nicks:
                id_gold = i.replace("\n", "").replace(" ", "").split(":")
                key = id_gold[0]
                gold = 0 if len(id_gold) == 1 else id_gold[1]
                if key not in loaded_dict:
                    loaded_dict[key] = {"data": date, "gold": int(gold)}

        f.seek(0)  # Перемещение курсора в начало файла
        f.truncate()  # Очистка содержимого файла
        pickle.dump(loaded_dict, f)
        p_log(f"Данные успешно обновлены в файл {name_file}. Всего {len(loaded_dict)} записей")


def read_pickle_file(name_file=NICKS_GAMER):
    with open(f"{name_file}", 'rb') as f:
        loaded_dict = pickle.load(f)
        # dct = {k: v for k, v in sorted(loaded_dict.items(), key=lambda item: item[1]['spoil'], reverse=True)}
        # p_log(f"Коровки дадут {sum(x['spoil'] for x in loaded_dict.values())} серебра")
        for key, value in loaded_dict.items():
            p_log(f'{key}:{value}')


def test_pars():
    with open("duel.html", 'rb') as fff:
        soup = BeautifulSoup(fff, 'lxml')
        result = soup.find('h1').text
        p_log(result == 'Дуэль')


def post_dragon(buy_rubies=''):
    payload = {
        'chooseMission': 'DragonLair',
        'missionArt': 'small',
        'missionKarma': 'Good',
        'buyRubies': f"{buy_rubies}"
    }
    post_url = 'https://s32-ru.battleknight.gameforge.com/world/location/'
    post_request(post_url, payload)
    p_log(f"Атака выполнена успешно, потрачено {buy_rubies if buy_rubies else '0'} рубинов")

    time_sleep()


def orden_message(message):
    payload = {
        'noCache': f'{int(time.time() * 1000)}',
        'text': "",
        'subject': message
    }
    post_request(url_orden_message, payload)


def click():
    # ________________________ Для прохождения группы ____________________________
    check_time_sleep(start_hour='21:15', end_hour='21:29', sleep_hour='21:30')

    if is_time_between(start_hour='21:29', end_hour='21:35'):
        go_group(60 * 30)
        timer_group = check_progressbar()
        if timer_group:
            p_log(f"Ожидание после группы {format_time(timer_group)}. Ожидаем...")
        time_sleep(timer_group)
    # _____________________________________________________________________________

    break_outer = False
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'lxml')

    a_tags = soup.find_all('a', onclick=lambda
        onclick: onclick and "chooseMission('small', 'DragonLair', 'Good', this)" in onclick)

    if a_tags:
        for a_tag in a_tags:
            if 'disabledSpecialBtn' in a_tag.get('class', []):
                buy_rubies_tags = soup.find_all('a', class_='devSmall missionBuyRubies toolTip',
                                                onclick=lambda onclick: onclick and
                                                                        "chooseMission('small', 'DragonLair', 'Good', '1')")
                if buy_rubies_tags:
                    for buy_rubies_tag in reversed(buy_rubies_tags):
                        onclick_value = buy_rubies_tag.get('onclick')
                        if onclick_value:
                            parts = onclick_value.split(',')
                            if len(parts) > 4:
                                fifth_argument = parts[4].strip().strip("');")
                                post_dragon(buy_rubies=fifth_argument)
                                break_outer = True
                                break
                    if break_outer:
                        break
        else:
            post_dragon()
    else:
        p_log('Не удалось найти тег <a> с нужным атрибутом onclick.')


if __name__ == "__main__":
    # set_initial_gold()
    # online_tracking_only()
    # time_sleep()
    # while True:
    #     online_tracking()
    #     time_sleep()
    # reduce_experience()
    # online_tracking_only()
    # korovk_reduce_experience(name_file="/pickles_data/korov.pickle")
    setup_logging()
    account_verification()
    while True:
        click()
    # create_pickle_file()
    # change_pickle_file(name_file=GOLD_GAMER)
    # read_pickle_file(name_file=GOLD_GAMER)
    # test_pars()
    # set_initial_gold()
