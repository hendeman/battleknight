import argparse
from typing import Any, Optional


class FilteredHelpParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.argument_groups = {}  # Хранит группы аргументов

    def add_argument(self, *args, **kwargs):
        """Переопределяем add_argument для поддержки filter_group"""
        filter_group = kwargs.pop('filter_group', None)

        # Вызываем оригинальный add_argument
        action = super().add_argument(*args, **kwargs)

        # Регистрируем аргумент в группе если указано
        if filter_group:
            if filter_group not in self.argument_groups:
                self.argument_groups[filter_group] = []
            self.argument_groups[filter_group].extend(action.option_strings)

        return action

    def print_help(self, filter_group: Optional[str] = None, file: Any = None) -> None:

        # Выводим основные разделы
        self._print_message("Утилита для работы с pickle-файлами\n\n", file)

        # Выводим доступные команды с фильтрацией
        self._print_message("\nДоступные команды:\n", file)

        for action in self._actions:

            # Применяем фильтрацию
            if filter_group:
                # Показываем только аргументы из указанной группы
                if filter_group in self.argument_groups:
                    group_args = self.argument_groups[filter_group]
                    if not any(opt in action.option_strings for opt in group_args):
                        continue
                else:
                    # Если группы не существует, пропускаем все
                    continue

            if action.option_strings:
                options = ', '.join(action.option_strings)
                if action.metavar:
                    options += f' {action.metavar}'
                self._print_message(f"  {options:<25} {action.help or ''}\n", file)

        # Выводим примеры использования
        self._print_message("\nПримеры:\n", file)
        if filter_group == 'pickle':
            self._print_message("  python main.py -rp nicks\n", file)
            self._print_message("  python main.py -cp nicks\n", file)
            self._print_message("  python main.py -up nicks\n", file)

        elif filter_group == 'statistic':
            self._print_message("  python main.py -wf\n", file)
            self._print_message("  python main.py -ps -wf\n", file)

        elif filter_group == 'group':
            self._print_message("  python main.py -gr\n", file)

        elif filter_group is None:
            # Полная справка - показываем все примеры
            self._print_message("  python main.py -rp data          # Чтение pickle-файла\n", file)
            self._print_message("  python main.py -ts users         # Статистика по пользователям\n", file)
            self._print_message("  python main.py --help            # Полная справка\n", file)


def arg_parser():
    """Настройка парсера аргументов."""
    parser = FilteredHelpParser(description='Выбор программы', add_help=False)

    parser.add_argument('-gr',
                        '--group',
                        action='store_true',
                        help='Включить прохождение группы',
                        filter_group="group")
    parser.add_argument('-ps',
                        '--program_selection',
                        action='store_true',
                        help='Статистика сервера, по умолчанию статистика ордена',
                        filter_group="statistic")
    parser.add_argument('-wf',
                        '--write_flag',
                        action='store_true',
                        help='Записать данные в файл',
                        filter_group="statistic")
    parser.add_argument('-rp',
                        '--read_pickle',
                        type=str,
                        metavar="FILENAME",
                        help='Прочитать pickle-файл',
                        filter_group="pickle")
    parser.add_argument('-cp',
                        '--create_pickle',
                        type=str,
                        metavar="FILENAME",
                        help='Создать pickle-файл',
                        filter_group="pickle")
    parser.add_argument('-chp',
                        '--change_pickle',
                        type=str,
                        metavar="FILENAME",
                        help='Изменить pickle-файл',
                        filter_group="pickle")

    return parser
