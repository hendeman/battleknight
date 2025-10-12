from logs.logs import p_log, setup_logging
from module.all_function import time_sleep, get_config_value, format_time
from module.cli import arg_parser
from module.game_function import is_time_between, check_progressbar, check_time_sleep, account_verification, \
    activate_karma, click, Namespace
from module.group import go_group
from module.ruby_manager import ruby_manager


def main_loop_click(group=False):
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

        if result == Namespace.MISSION_RUBY:
            ruby_manager.mark_ruby_used()
            p_log(
                f"Дневной лимит: {ruby_manager.daily_used}/{ruby_manager.daily_limit}, "
                f"Всего: {ruby_manager.total_used}/{ruby_manager.total_limit}")
        if result == Namespace.NOT_MISSION:
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
