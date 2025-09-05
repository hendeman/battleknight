from datetime import datetime
from enum import Enum, auto

from bs4 import BeautifulSoup

from logs.logs import p_log, setup_logging
from module.all_function import time_sleep, get_config_value, format_time
from module.cli import arg_parser
from module.game_function import is_time_between, check_progressbar, check_time_sleep, account_verification, \
    activate_karma, post_dragon
from module.group import go_group
from module.http_requests import make_request
from setting import world_url


class ClickResult(Enum):
    MISSION = auto()  # Обычная миссия
    MISSION_RUBY = auto()  # Миссия с рубинами
    NOT_MISSION = auto()  # Нет свободных миссий


class RubyManager:
    def __init__(self, total_limit, daily_limit):
        self.total_limit = total_limit
        self.daily_limit = daily_limit
        self.total_used = 0
        self.daily_used = 0
        self.last_reset_date = datetime.now().date()

    def should_use_rubies(self):
        # Проверяем смену дня
        if datetime.now().date() != self.last_reset_date:
            self.daily_used = 0
            self.last_reset_date = datetime.now().date()
            p_log("Новый день, сбрасываем счетчик рубинов")

        # Возвращаем True если можно использовать рубины
        return self.daily_used < self.daily_limit and self.total_used < self.total_limit

    def mark_ruby_used(self):
        self.total_used += 1
        self.daily_used += 1


def click(mission_duration, mission_name, find_karma, rubies=False):
    response = make_request(world_url)
    soup = BeautifulSoup(response.content, 'lxml')

    search_string = f"chooseMission('{mission_duration}', '{mission_name}', '{find_karma}', this)"
    a_tags = soup.find('a', onclick=lambda onclick: onclick and search_string in onclick)

    if a_tags:
        if 'disabledSpecialBtn' in a_tags.get('class', []):
            onclick_pattern = f"chooseMission('{mission_duration}', '{mission_name}', '{find_karma}', this, '1')"
            buy_rubies_tags = soup.find('a', class_='devSmall missionBuyRubies toolTip',
                                        onclick=lambda onclick: onclick and onclick_pattern in onclick)
            if buy_rubies_tags and rubies:
                onclick_value = buy_rubies_tags.get('onclick')
                if onclick_value:
                    parts = onclick_value.split(',')
                    if len(parts) > 4:
                        fifth_argument = parts[4].strip().strip("');")
                        post_dragon(mission_duration, mission_name, find_karma, buy_rubies=fifth_argument)
                        return ClickResult.MISSION_RUBY
            return ClickResult.NOT_MISSION

        else:
            post_dragon(mission_duration, mission_name, find_karma)
            return ClickResult.MISSION
    else:
        p_log(f'Не удалось найти тег <a> с нужным атрибутом onclick.', level='error', is_error=True)
        raise TypeError('Не удалось найти тег <a> с нужным атрибутом onclick')


def main_loop_click(group=False):
    ruby_manager = RubyManager(
        get_config_value("rubies_limit"),
        get_config_value("rubies_day")
    )
    karma_activate = get_config_value("karma_activate")
    if karma_activate:
        activate_karma(skill=get_config_value("karma_activate_name"),
                       count=get_config_value("karma_activate_day"))
    while ruby_manager.total_used < ruby_manager.total_limit:

        # ________________________ Для прохождения группы ____________________________
        check_time_sleep(start_hour='21:15', end_hour='21:29', sleep_hour='21:30')

        if group and is_time_between(start_hour='21:29', end_hour='21:35'):
            go_group(get_config_value("group_wait"))
            timer_group = check_progressbar()
            if timer_group:
                p_log(f"Ожидание после группы {format_time(timer_group)}. Ожидаем...")
            time_sleep(timer_group)
        # _____________________________________________________________________________

        # Определяем, использовать ли рубины в этой итерации
        use_rubies = ruby_manager.should_use_rubies()

        game_param = [
            get_config_value("mission_duration"),
            get_config_value("mission_name"),
            get_config_value("working_karma").capitalize()
        ]

        result = click(*game_param, rubies=use_rubies)

        if result == ClickResult.MISSION_RUBY:
            ruby_manager.mark_ruby_used()
            p_log(
                f"Дневной лимит: {ruby_manager.daily_used}/{ruby_manager.daily_limit}, "
                f"Всего: {ruby_manager.total_used}/{ruby_manager.total_limit}")
        if result == ClickResult.NOT_MISSION:
            p_log(f"Свободных миссий больше нет. Пауза для восстановления очков...")
            check_time_sleep(start_hour='00:00', end_hour='21:16', sleep_hour='21:30')
            check_time_sleep(start_hour='21:31', end_hour='04:00', sleep_hour='08:00')

    p_log("Достигнут общий лимит рубинов")


if __name__ == "__main__":
    setup_logging()
    account_verification(helper_init=False)
    parser = arg_parser()
    args = parser.parse_args()
    if args.group:
        p_log(f"Запущен скрипт с прохождением группы")
        main_loop_click(group=True)
    else:
        main_loop_click()
