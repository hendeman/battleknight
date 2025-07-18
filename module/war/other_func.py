import os
import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from tqdm import tqdm

from logs.logs import p_log
from module.all_function import get_config_value
from module.game_function import progressbar_ends, seconds_to_hhmmss
from module.http_requests import make_request
from module.war.settings import html_files_directory, url_clanwar


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
