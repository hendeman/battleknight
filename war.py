import threading

from logs.logs import setup_logging
from module.all_function import get_config_value
from module.game_function import account_verification
from module.http_requests import post_request
from module.war.html_parser import main_pars_clanwar
from module.war.members_operation import remove_members, accept_into_order
from module.war.other_func import *
from module.war.settings import *

stop_event = threading.Event()


def attack_castle(trade_name, delete_war_list=None):
    p_log("Будет отправлен запрос на проверку статуса войны")
    decorated_get_request = deco_time(make_request)
    resp = decorated_get_request(url_status_war, game_sleep=False)
    save_html_file(trade_name, resp, 'check')

    soup = BeautifulSoup(resp.text, 'lxml')
    sec = progressbar_ends(soup)
    p_log(f"Таймер sec: {sec}, stop_event: {stop_event.is_set()}", level='debug')
    if not sec and not stop_event.is_set():
        stop_event.set()
        castle_id = main_pars_clanwar(str(soup))
        if castle_id:
            p_log(f"Война окончена, будет отправлен запрос на захват - {castle_id}")

            try:
                if delete_war_list:
                    remove_members(mode='var', delete_war_list=delete_war_list)
                    time.sleep(get_config_value(key='remove_member_time_sleep'))
            except Exception as er:
                p_log(f"Ошибка при удалении игроков после окончания войны: {er}")

            if get_config_value(key='leave_clan'):
                p_log("Будет осуществлена попытка выйти из ордена")
                decorated_get_request = deco_time(make_request)  # тут пост или гет проверить
                resp = decorated_get_request(url_clan_leave, game_sleep=False)
            else:
                payload = {'castleID': castle_id, 'warType': 'conquer'}
                decorated_post_request = deco_time(post_request)
                resp = decorated_post_request(url_attack_castle, payload)
                save_html_file(trade_name, resp, 'answer')
        else:
            p_log(f"Запрос {trade_name}. Ошибка получения castle_id")
    else:
        p_log(f"Запрос {trade_name} оказался холостым")


def capture_castle(delete_war_list):
    threads = []
    for i in range(1, 8):
        if stop_event.is_set():  # Проверяем флаг перед запуском нового потока
            break
        thread = threading.Thread(target=attack_castle, args=(f"trade_name{i}", delete_war_list,))
        threads.append(thread)
        thread.start()
        time.sleep(0.5)  # Задержка перед запуском следующего потока
    for thread in threads:
        thread.join()


def check_status_war():
    while True:
        time_end, sec, soup = get_time_end()
        p_log(f"Время до следующего раунда {time_end}")
        if sec:
            war_init = soup.find('div', id='clanwarInitiator').text
            p_log(war_init)
            battle_round_status = soup.find('div', class_='battlerounds')

            if battle_round_status:
                battle_round = int(battle_round_status.text.split()[1])
                p_log(f'Текущий раунд: {battle_round}')
                if battle_round < 9:
                    p_log("Ожидание 8 часов...")
                    time_sleep(8 * 3600)
                else:
                    stop_event.clear()
                    # Синхронизация времени грубая за час
                    wait_until_target_time(time_end, delay=60 * 60)

                    time_end, sec, soup = get_time_end()
                    wait_until_target_time(time_end, delay=3 * 60)
                    delete_war_list = None
                    try:
                        if get_config_value(key='be_remove_member_flag'):
                            delete_war_list = remove_members('be_var')
                    except Exception as er:
                        p_log(f"Ошибка при удалении игроков до начала войны: {er}")

                    time_end, sec, soup = get_time_end()
                    wait_until_target_time(time_end)
                    if get_config_value(key='activate_attack_castle'):
                        capture_castle(delete_war_list)
                        time.sleep(10)
                        """
                            Далее идет проверка на неверное время от сервера. Очень редко после окончания таймера
                            войны сервер выдает снова 9 раунд
                        """
                        while True:
                            time_end, sec, soup = get_time_end()
                            p_log(f"Время до следующего раунда {time_end}")
                            if sec:
                                war_init = soup.find('div', id='clanwarInitiator').text
                                p_log(war_init)
                                battle_round_status = soup.find('div', class_='battlerounds')

                                if battle_round_status:
                                    battle_round = int(battle_round_status.text.split()[1])
                                    p_log(f'Текущий раунд: {battle_round}')
                                    if battle_round == 9:
                                        time.sleep(10)
                                        continue
                                else:
                                    break
                            else:
                                stop_event.clear()
                                capture_castle(delete_war_list)
                                break
            else:

                thread = threading.Thread(target=accept_into_order, daemon=True)
                thread.start()

                p_log("Раунды еще не начались")
                p_log("Ожидание 1 день 4 часа...")
                time_sleep(1 * 24 * 3600 + 9 * 3600)
        else:
            p_log("Запрос был отправлен слишком рано, либо замок был занят")
            break


if __name__ == "__main__":
    setup_logging(enable_rotation=False, log_file_path="logs/app_war.log")
    account_verification()
    wait_until("17:00:00")
    check_status_war()
