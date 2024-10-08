import pickle
import json
import re
import time

from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from logs.logs import p_log
from module.all_function import current_time, time_sleep, get_config_value
from module.data_pars import heals, pars_gold_duel
from module.http_requests import make_request, post_request
from setting import status_list, waiting_time, status_list_eng

date = datetime(2024, 9, 17, 19)

url_compare = 'https://s32-ru.battleknight.gameforge.com/duel/compare/?enemyID='
url = "https://s32-ru.battleknight.gameforge.com/duel/duel/?enemyID="
url_group = 'https://s32-ru.battleknight.gameforge.com/groupmission/group/'
url_orden_message = "https://s32-ru.battleknight.gameforge.com/ajax/board/sendmessage"
url_ordermail = "https://s32-ru.battleknight.gameforge.com/mail/ordermail"
url_nicks = "nicksflower.txt"


def make_attack(nick, heals_point=False):
    url_fight = url + str(nick)
    p_log(f"Попытка атаки на {nick}")
    resp = make_request(url_fight)
    status_duel = get_status(resp)
    # result = 0

    if status_duel == 'Дуэль':
        p_log(f"Атака {nick} произведена успешно")
        return True, resp

    while status_duel in status_list:
        index = status_list.index(status_duel)
        p_log(f"lupatik status: {status_duel}")
        time_sleep()
        p_log(f"Попытка атаки на {nick}")
        resp = make_request(url_fight)
        if resp.url == "https://s32-ru.battleknight.gameforge.com:443/common/error":
            handle_error(resp, nick)
            return False, resp
        status_duel = get_status(resp)

        if status_duel == 'Дуэль':
            p_log(f"Атака на {nick} произведена успешно")
            return True, resp

    handle_error(resp, nick, heals_point=heals_point)
    heals(resp)
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


def handle_error(resp, nick, heals_point=False):
    if heals(resp) == 1:
        if heals_point:
            from game_play import use_potion
            use_potion()
        else:
            p_log("Отдыхаем 10 минут, пока не восстановится здоровье")
            time_sleep()
    elif check_status_group():
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
            else:
                p_log("Нет совпадений. Проверке парсинг состония дуэли")
        except Exception:
            p_log("Рыцарь недоступен, либо был атакован в течение 12 часов", level='warning')

    return


def get_gold_for_player(gamer) -> int:
    url_gamer = f'https://s32-ru.battleknight.gameforge.com/common/profile/{gamer}/Scores/Player'
    resp = make_request(url_gamer)
    time.sleep(0.5)
    soup = BeautifulSoup(resp.text, 'lxml')
    gold = int(soup.find('table', class_='profileTable').find_all('tr')[3].text.split()[2])
    return gold


def update_players_gold(dict_gamer, list_of_players):
    for gamer in list_of_players:
        list_of_players[gamer].setdefault('time',
                                          dict_gamer[gamer].get('time', date) if gamer in dict_gamer else date)
        list_of_players[gamer].setdefault('win_status',
                                          dict_gamer[gamer].get('win_status', None) if gamer in dict_gamer else None)
        list_of_players[gamer].setdefault('spoil',
                                          dict_gamer[gamer].get('spoil', None) if gamer in dict_gamer else None)
        list_of_players[gamer]["gold"] = get_gold_for_player(gamer)

    return list_of_players

    # for gamer in list_of_players:
    #     gold = get_gold_for_player(gamer)
    #     if gamer not in dict_gamer:
    #         dict_gamer[gamer] = {"gold": gold, "time": date,
    #                              "name": list_of_players[gamer]['name'], "gold_diff": list_of_players[gamer]['gold_diff']}
    #     else:
    #         dict_gamer[gamer]["gold"] = gold
    #         dict_gamer[gamer]["gold_diff"] = list_of_players[gamer]['gold_diff']
    # return dict_gamer


def set_initial_gold():
    with open('battle.json', 'r', encoding='utf-8') as file:
        list_of_players = json.load(file)

    try:
        with open("gamer_gold.pickle", 'rb') as file_gamer:
            p_log("Сканирование добычи игроков...")
            dict_gamer = pickle.load(file_gamer)

    except FileNotFoundError:
        p_log("Файла не существует, будет создан новый", level='warning')
        dict_gamer = {}

    filtered_dct = update_players_gold(dict_gamer, list_of_players)

    # filtered_dct = {key: dict_gamer[key] for key in list_of_players}
    with open("gamer_gold.pickle", 'wb') as file_gamer:
        pickle.dump(filtered_dct, file_gamer)
        p_log("Файл игроков успешно сохранен", level='debug')


def online_tracking():
    with open("gamer_gold.pickle", 'rb') as file_gamer:
        p_log("online_tracking", level='debug')
        dict_gamer = pickle.load(file_gamer)
        filtered_data = {key: value for key, value in dict_gamer.items() if
                         (datetime.now() - value['time']) > timedelta(hours=12)}
        if not filtered_data:
            p_log("В gamer_gold.pickle нападать не на кого")
            return False

        for gamer in filtered_data:
            time_str, current_date = current_time()
            gold = get_gold_for_player(gamer)
            gold_diff = gold - filtered_data[gamer]['gold']
            gold_diff_proc = int(gold_diff / filtered_data[gamer]['gold_diff'] * 100)
            p_log(f"{gamer} {filtered_data[gamer]['name']} накопил {gold_diff} [{gold_diff_proc}%] серебра")

            if gold - filtered_data[gamer]["gold"] > filtered_data[gamer]['gold_diff']:
                flag, resp = make_attack(gamer, heals_point=True)
                if flag:
                    received_gold, win_status = pars_gold_duel(resp, gold_info=True, win_status=True)
                    dict_gamer[gamer]["time"] = current_date
                    dict_gamer[gamer]["win_status"] = win_status
                    dict_gamer[gamer]["spoil"] = received_gold

                    # Отправить в орден коровку
                    if win_status == "lupatik выиграл" and received_gold > 100:
                        p_log(win_status)
                        p_log(f"{filtered_data[gamer]['name']} +{received_gold}")
                        if get_config_value(key='order_message'):
                            message = f"{filtered_data[gamer]['name']} +{received_gold}"
                            make_request(url_ordermail)
                            orden_message(message)
                            p_log("Отправлено сообщение в орден")

                    with open("gamer_gold.pickle", 'wb') as file_gamer:
                        pickle.dump(dict_gamer, file_gamer)
                    time_sleep()
                    return "sleep"
        return True


def online_tracking_only():
    while True:
        status_sleep = online_tracking()
        if status_sleep == "sleep":
            continue
        if status_sleep:
            time_sleep()
        else:
            break


def reduce_experience(name_file="nicks.pickle"):
    # setup_logging()
    with open(name_file, 'rb') as f:
        loaded_dict = pickle.load(f)
        sorted_dict = {k: v for k, v in sorted(loaded_dict.items(), key=lambda item: item[1]['gold'])}

        # number_of_attacks задается из config.ini - количесвто проводимых атак
        number_of_attacks = get_config_value(key="number_of_attacks")

        for nick in sorted_dict:
            time_str, current_date = current_time()
            difference_data = current_date - loaded_dict[nick]["data"]
            if int(difference_data.total_seconds() / 3600) >= 12:
                flag, resp = make_attack(nick)
                if flag:
                    received_gold = pars_gold_duel(resp, gold_info=True)
                    if not number_of_attacks:
                        break
                    number_of_attacks -= 1

                    loaded_dict[nick]["data"] = current_date
                    loaded_dict[nick]["gold"] = received_gold
                    with open(name_file, 'wb') as f:
                        pickle.dump(loaded_dict, f)
                    p_log("Ожидание 10 мин перед следующей атакой...")
                    time_sleep()
                    # online_track = 1 tracking active from config.ini
                    if get_config_value(key="online_track"):
                        online_tracking()  # функция нахождения и атаки на играющих игроков
            else:
                p_log(f"{nick} не может быть атакован")
        # когда закончилился список из рыцаряй для слива опыта
        if get_config_value(key="online_track"):
            online_tracking_only()


def korovk_reduce_experience(name_file="nicks.pickle"):
    def update_knight_data(loaded_dict, nick, current_date, received_gold):
        loaded_dict[nick]["data"] = current_date
        loaded_dict[nick]["gold"] = received_gold
        with open(name_file, 'wb') as f:
            pickle.dump(loaded_dict, f)

    with open(name_file, 'rb') as f:
        loaded_dict = pickle.load(f)
        sorted_dict = {k: v for k, v in sorted(loaded_dict.items(), key=lambda item: item[1]["gold"], reverse=True)}
        list_fail = []
        while sorted_dict or list_fail:
            for nick in list(sorted_dict.keys()):
                time_str, current_date = current_time()
                difference_data = current_date - loaded_dict[nick]["data"]
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


def change_pickle_file(name_file="gamer_gold.pickle"):
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


def create_pickle_file(name_file="nicks.pickle"):
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


def read_pickle_file(name_file="nicks.pickle"):
    with open(f"{name_file}", 'rb') as f:
        loaded_dict = pickle.load(f)
        dct = {k: v for k, v in sorted(loaded_dict.items(), key=lambda item: item[1]["gold"], reverse=True)}
        p_log(f"Коровки дадут {sum(x['gold'] for x in loaded_dict.values())} серебра")
        for key, value in dct.items():
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


def click(url="https://s32-ru.battleknight.gameforge.com/world"):
    break_outer = False
    response = make_request(url)
    soup = BeautifulSoup(response.content, 'html.parser')

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
    # name_file_pickle = "gamer_gold.pickle" # "nicks.pickle" or "gamer_gold.pickle" or "new_nicks.pickle" or "korov.pickle"
    set_initial_gold()
    online_tracking_only()
    # time_sleep()
    # while True:
    #     online_tracking()
    #     time_sleep()
    # reduce_experience()
    # online_tracking_only()
    # korovk_reduce_experience(name_file="korov.pickle")
    # while True:
    #     click()
    # create_pickle_file()
    # change_pickle_file(name_file="gamer_gold.pickle")
    # read_pickle_file(name_file="gamer_gold.pickle")
    # test_pars()
    # set_initial_gold()
