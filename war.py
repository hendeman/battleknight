import threading

from logs.logging_config import setup_logging_system, cleanup_logging_system
from module.all_function import time_sleep_main, format_time, check_file_exists
from module.game_function import account_verification
from module.http_requests import post_request
from module.war.cli import war_parser
from module.war.html_parser import main_pars_clanwar
from module.war.members_operation import remove_members, accept_into_order
from module.war.other_func import *
from module.war.settings import *

stop_event = threading.Event()


def attack_castle(trade_name, castle_info=None, delete_war_list=None):
    p_log("Будет отправлен запрос на проверку статуса войны")
    decorated_get_request = deco_time(make_request)
    resp = decorated_get_request(url_status_war, game_sleep=False)

    soup = BeautifulSoup(resp.text, 'lxml')
    sec = None
    castle_id = None

    # Определяем режим работы: обычная атака или атака врага
    if castle_info:
        # Режим атаки врага
        if soup.find('div', id=castle_info[0]).has_attr('onclick'):
            sec = False
            castle_id = castle_info[1].get('castleID')
            save_html_file(trade_name, resp, 'open')
    else:
        # Обычный режим атаки
        save_html_file(trade_name, resp, 'check')
        sec = progressbar_ends(soup)
        if not sec:
            castle_id = main_pars_clanwar(str(soup))

    p_log(f"Таймер: {format_time(sec)}, stop_event: {stop_event.is_set()}", level='debug')

    if not sec and not stop_event.is_set() and castle_id:
        stop_event.set()
        p_log(f"Война окончена, будет отправлен запрос на захват - {castle_id}")

        # Удаление игроков (только для обычного режима)
        if delete_war_list:
            try:
                remove_members(mode='var', delete_war_list=delete_war_list)
                time.sleep(get_config_value(key='remove_member_time_sleep'))
            except Exception as er:
                p_log(f"Ошибка при удалении игроков после окончания войны: {er}")

        # Выход из ордена или атака
        if not castle_info and get_config_value(key='leave_clan'):
            p_log("Будет осуществлена попытка выйти из ордена")
            decorated_get_request(url_clan_leave, game_sleep=False)
        else:
            payload = {'castleID': castle_id, 'warType': 'conquer'}
            decorated_post_request = deco_time(post_request)
            resp = decorated_post_request(url_attack_castle, payload)
            save_html_file(trade_name, resp, 'answer')
    else:
        p_log(f"Запрос {trade_name} оказался холостым")


def capture_castle(delete_war_list=None, castle_info=None):
    max_concurrent = 10  # Максимально количество одновременных потоков
    semaphore = threading.Semaphore(max_concurrent)

    threads = []
    max_threads = 120 if castle_info else 7

    def limited_attack(*arge):
        with semaphore:  # Semaphore ограничивает одновременный доступ
            return attack_castle(*arge)

    for i in range(1, max_threads + 1):
        if stop_event.is_set():
            break

        # Создаем аргументы в зависимости от режима
        if castle_info:
            arg = (f"trade_name{i}", castle_info)
        else:
            arg = (f"trade_name{i}", None, delete_war_list)

        thread = threading.Thread(target=limited_attack, args=arg)
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
                    time_wait = (9 - battle_round) * 8 * 60 * 60 + sec - 60 * 60
                    p_log(f"Ожидание: {format_time(time_wait)}")
                    time_sleep_main(time_wait, interval=8 * 3600, name="До конца войны")
                else:
                    stop_event.clear()
                    # Синхронизация времени грубая за 30 минут
                    wait_until_target_time(time_end, delay=30 * 60)

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
                if get_config_value("accept_into_order"):
                    thread = threading.Thread(target=accept_into_order, daemon=True)
                    thread.start()

                p_log("Раунды еще не начались")
                p_log("Ожидание 1 день 4 часа...")
                time_sleep(1 * 24 * 3600 + 9 * 3600)
        else:
            p_log("Запрос был отправлен слишком рано, либо замок был занят")
            break


def capture_enemy_castle(tag_castle='cf1'):
    decorated_get_request = deco_time(make_request)
    resp = decorated_get_request(url_status_war, game_sleep=False)
    soup = BeautifulSoup(resp.text, 'lxml')

    castles_dict = main_pars_clanwar(str(soup), save=False)
    castle_info = castles_dict.get(tag_castle, None)
    if castles_dict:
        tip = castles_dict.get(tag_castle).get('tip')
        time_difference = get_time_difference(tip)
        if time_difference:
            time_sleep_main(time_difference, interval=1800, name="До захвата осталось: ")
        capture_castle(delete_war_list=None, castle_info=(tag_castle, castle_info))
    else:
        p_log(f'Замок {tag_castle} не найден', level='error', is_error=True)


if __name__ == "__main__":
    queue, logging_process, translate = setup_logging_system(enable_rotation=False, log_file_path="war")
    # setup_logging(enable_rotation=False, log_file_path="war")
    account_verification(helper_init=False)
    if not check_file_exists(data_files_directory, members):
        p_log(f"Файл {members} не найден. Будет создан новый")
        match_clan(create_file=True)
    parser = war_parser()
    args = parser.parse_args()
    if args.save:
        p_log(f"Программа сохранения замка")
        check_status_war()
    elif args.capture:
        p_log(f"Программа захвата вражеского замка: '{args.capture}'")
        capture_enemy_castle(args.capture)
    elif args.clan:
        p_log("Программа обновления списка участников ордена")
        match_clan()
    elif args.read:
        kick_gamers = get_kick_members()
        if kick_gamers:
            p_log(f"Игроки, которые будут удалены из ордена: {', '.join(kick_gamers)}")
        else:
            p_log("Никто не будет удален из ордена")
    elif args.set:
        if 'reset' in args.set:
            p_log(f"Будет сброшен статус удаления из ордена для всех игроков")
            set_kick_members('reset')
        else:
            p_log(f"Удалить из ордена следующие имена: {args.set}")
            set_kick_members(args.set)
    else:
        parser.print_help()
    cleanup_logging_system(queue, logging_process, translate)
