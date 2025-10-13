import json
import re
import threading
import time

from bs4 import BeautifulSoup

from logs.logs import p_log
from module.data_pars import party
from module.http_requests import post_request, make_request
from module.war.other_func import deco_time
from module.war.settings import war_list, url_members, SERVER, url_war_damage


@deco_time
def post_remove_member(id_name):
    current_thread_name = threading.current_thread().name
    p_log(f"Попытка отправить запрос на удаление {current_thread_name}")
    url_remove_member = f"{SERVER}/ajax/clan/removeMember/?knightID={id_name}"
    payload = {'knightID': id_name}
    try:
        resp = post_request(url_remove_member, payload).json()
        if resp["result"]:
            p_log(f"{current_thread_name} успешно удален из ордена")
        else:
            p_log(f'Неудача. Причина: {resp.get("reason")}')
    except Exception as err:
        p_log(f'Ошибка запроса удаления игрока: {err}')


def remove_members(mode='var', delete_war_list=None):
    mode_status = {'be_var': "Во время битвы", 'var': "После битвы"}
    if mode == 'var' and delete_war_list is None:
        return 0

    with open(war_list, 'r', encoding="utf-8-sig") as file:
        party_members = json.load(file)
        list_of_players = dict(filter(lambda item: item[1].get('clan_kick'), party_members.items()))

    remove_member_list = list_of_players if mode == 'be_var' else delete_war_list
    remove_member_list_not_war, remove_member_list_in_war = {}, {}

    if mode == 'be_var':
        resp = make_request(url_members, game_sleep=False)
        soup = BeautifulSoup(resp.text, 'lxml')
        dct = party(soup)
        filtered_dict = dict(filter(lambda item: item[0] in dct, remove_member_list.items()))
        p_log(f"filtered_dict: {filtered_dict}", level="debug")

        # Получение списка игроков, которые участвуют в текущей битве
        try:
            resp = make_request(url_war_damage).json()
            war_members = [x.get('id') for x in resp['data']['attacker']['member']]
            p_log(f"war_members: {war_members}", level='debug')
        except Exception as er:
            p_log(f"Ошибка получения списка воющих игроков: {er}")
            war_members = remove_member_list

        # Разделение списка игроков на воюющих в данной битве невоюющих
        for gamer_id, value in filtered_dict.items():
            if gamer_id in war_members:
                remove_member_list_in_war[gamer_id] = value
            else:
                remove_member_list_not_war[gamer_id] = value

        p_log(f"remove_member_list_not_war: {remove_member_list_not_war}", level="debug")
        p_log(f"remove_member_list_in_war: {remove_member_list_in_war}", level="debug")

        remove_member_list = remove_member_list_not_war

    remove_member_name_list = list(map(lambda game_id: remove_member_list.get(game_id).get('name'), remove_member_list))
    p_log(f"{mode_status.get(mode)} будут удалены следующие игроки {remove_member_name_list}")

    threads = [
        threading.Thread(target=post_remove_member,
                         name=remove_member_list[id_name].get("name"),
                         args=(id_name,),
                         daemon=True)
        for id_name in remove_member_list]
    for thread in threads:
        thread.start()
        if mode == 'be_var':
            time.sleep(0.5)
    # for thread in threads:
    #     thread.join()
    if mode == 'be_var':
        return remove_member_list_in_war


# _______________________________________________________________________________________________


def set_knight_rank(player, name, rank):
    p_log(f"Попытка назначить {name} ранг {rank}")
    payload = {'knightID': player, f"rankID{player}": rank}
    post_request(url_members, payload)


def get_applications_ids(soup):
    """ Парсинг игроков, которые просятся в орден"""
    pattern = re.compile(r"recordApplier(\d+)")
    records = soup.find_all('tr', id=pattern)
    numbers = []
    for record in records:
        match = pattern.search(record['id'])
        if match:
            numbers.append(match.group(1))  # или int(match.group(1)), если нужно число
    return numbers


def knight_accept(player, name):
    p_log(f"Попытка принять {name} в орден")
    payload = {'applierID': player}
    post_request(url_members, payload)


def is_rank_player(dict1, dict2):
    """
    :Словарь из protected_players.json dict1:
    :Словарь игроков ордена dict2:
    Проверка на наличие игроков в ордене из dict1, проверка ранга, установка ранга
    """
    players = set(dict1) & set(dict2)
    for player in players:
        target_rank, current_rank = dict1[player].get('rank'), dict2[player].get('rank')
        if target_rank != current_rank:
            name = dict1[player].get('name')
            p_log(f"У рыцаря {name} {current_rank} ранг")
            set_knight_rank(name=name,
                            player=player,
                            rank=target_rank)


def accept_into_order():
    p_log("Открылся поток для принятия заявок", level='debug')
    count = 5
    repeat_time = int(0.5 * 60 * 60)
    while count:
        with open(war_list, 'r', encoding="utf-8-sig") as file:
            remove_member_list = json.load(file)
        time.sleep(repeat_time)

        resp = make_request(url_members, game_sleep=False)
        soup = BeautifulSoup(resp.text, 'lxml')

        is_rank_player(remove_member_list, party(soup))

        list_numbers_app = get_applications_ids(soup)

        # фильтрация игроков, в списке members будут только доступные игроки из remove_member_list
        members = [
            remove_member_list[number_id].get('name')
            if number_id in remove_member_list
            else number_id
            for number_id in list_numbers_app
        ]
        p_log(f"В орден просятся: {', '.join(members)}" if members else 'Нет заявок в орден')
        for number_id in list_numbers_app:
            if number_id in remove_member_list:
                name = remove_member_list[number_id].get('name')
                knight_accept(player=number_id, name=name)
                time.sleep(2)
                set_knight_rank(name=name,
                                player=number_id,
                                rank=remove_member_list[number_id].get('rank'))
        repeat_time *= 2
        count -= 1
    p_log("Поток для принятия заявок завершился!", level='debug')
