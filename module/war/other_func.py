import os
import re
import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from tqdm import tqdm

from logs.logs import p_log
from module.all_function import get_config_value, load_json_file, save_json_file
from module.data_pars import party
from module.game_function import progressbar_ends, seconds_to_hhmmss
from module.http_requests import make_request
from module.war.settings import html_files_directory, url_clanwar, data_files_directory, members, url_members


def wait_until_target_time(time_end, delay=0):
    now = datetime.now()
    hours, minutes, seconds = map(int, time_end.split(':'))
    target_time = now + timedelta(hours=hours, minutes=minutes, seconds=seconds)
    time_difference = (target_time - now).total_seconds()
    if delay:
        time_sleep(int(time_difference - delay))
    else:
        p_log(f"Текущее время {get_current_time()}")
        p_log(f"До окончания битвы {time_end}")
        p_log(f"Ожидаем {time_difference} секунд ...")
        time.sleep(time_difference - get_config_value(key='atk_delay_tweak'))


def wait_until(target_time_str):
    p_log(f"Ожидаем до {target_time_str} ...")
    target_hour, target_minute, target_second = map(int, target_time_str.split(':'))
    now = datetime.now()
    target_time = now.replace(hour=target_hour, minute=target_minute, second=target_second, microsecond=0)
    if now > target_time:
        # Если время уже прошло, запланируем на следующий день
        target_time += timedelta(days=1)
    time.sleep((target_time - now).total_seconds())


def get_time_difference(text):
    # Извлекаем дату и время из строки
    pattern = r'(\d{2}\.\d{2}\.\d{4}) - (\d{2}:\d{2})'
    match = re.search(pattern, text)

    if not match:
        return None

    date_str = match.group(1)  # "28.08.2025"
    time_str = match.group(2)  # "02:20"

    # Преобразуем строку в объект datetime
    target_datetime = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")

    # Получаем текущее время
    current_datetime = datetime.now()

    # Вычисляем разницу в секундах
    time_difference = (target_datetime - current_datetime).total_seconds()

    return time_difference


def save_html_file(trade_name, resp, status):
    # Формируем полный путь к файлу
    file_path = os.path.join(html_files_directory, f'clanwar_{status}_{trade_name}.html')

    # Создаем директорию, если она не существует
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Сохраняем файл
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(resp.text)


def get_current_time():
    current_time = datetime.now()
    formatted_time = current_time.strftime("%H:%M:%S") + f".{current_time.microsecond:06d}"
    return formatted_time


def time_sleep(seconds):
    for _ in tqdm(range(seconds // 60), desc="Осталось времени", unit="мин"):
        time.sleep(60)


def deco_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        p_log(f"Текущее время {get_current_time()}")
        result = func(*args, **kwargs)
        p_log(f"Время запроса: {round(time.time() - start_time, 3)} сек")
        return result

    return wrapper


@deco_time
def get_time_end():
    resp = make_request(url_clanwar, game_sleep=False)
    soup = BeautifulSoup(resp.text, 'lxml')
    sec = progressbar_ends(soup)
    return seconds_to_hhmmss(sec), sec, soup


# _________________________________ Для формирования и обновления json игроков удаления _____________________
def remove_keys_from_nested(dictionary, keys_to_remove):
    """Удаляет указанные ключи из всех вложенных словарей и добавляет новый ключ."""
    for inner_dict in dictionary.values():
        for key in keys_to_remove:
            inner_dict.pop(key, None)
        inner_dict['clan_kick'] = 0
    return dictionary


def change_clan_dict(dct_new, dct_old):
    for gamer, param in dct_new.items():
        if gamer not in dct_old:
            p_log(f"Появился новый игрок {param.get('name')}")
            dct_old[gamer] = {
                'name': param.get('name'),
                'rank': param.get('rank'),
                'clan_kick': 0
            }
        else:
            name = param.get('name')
            rank = param.get('rank')
            if name != dct_old[gamer].get('name'):
                p_log(f'Игрок с id={gamer} изменил имя с {dct_old[gamer].get("name")} на {name}')
                dct_old[gamer]['name'] = name
            if param.get('rank') != dct_old[gamer].get('rank'):
                p_log(f'Игрок {name} изменил ранг с {dct_old[gamer].get("rank")} на {rank}')
                dct_old[gamer]['rank'] = param.get('rank')
    return dct_old


def match_clan(create_file=False):
    resp = make_request(url_members, game_sleep=False)
    soup = BeautifulSoup(resp.text, 'lxml')
    party_members = party(soup)
    if not create_file:
        party_members_old = load_json_file(data_files_directory, members)
        party_members_new = change_clan_dict(party_members, party_members_old)
        save_json_file(party_members_new, data_files_directory, members)
    else:
        save_json_file(remove_keys_from_nested(party_members, ['gold', 'level']),
                       data_files_directory, members)


def set_kick_members(members_list):
    party_members = load_json_file(data_files_directory, members)
    change_name = []

    if members_list == 'reset':
        # Сброс всех clan_kick
        for value in party_members.values():
            if value.get('clan_kick'):
                value['clan_kick'] = 0
                change_name.append(value.get('name'))
    else:
        # Создаем словарь для быстрого поиска по имени
        name_to_entry = {}
        for gamer_id, data in party_members.items():
            name_to_entry[data['name']] = (gamer_id, data)

        # Устанавливаем clan_kick
        for member in members_list:
            if member in name_to_entry:
                gamer_id, data = name_to_entry[member]
                data['clan_kick'] = 1
                change_name.append(member)

    if change_name:
        p_log(f"Изменен статус удаления у {', '.join(change_name)}")
        save_json_file(party_members, data_files_directory, members)


def get_kick_members():
    party_members = load_json_file(data_files_directory, members)
    return list(map(lambda x: x['name'],
                    filter(lambda x: x.get('clan_kick') == 1,
                           party_members.values())))
