import argparse


def war_parser():
    """Настройка парсера аргументов."""
    parser = argparse.ArgumentParser(description='Выбор программы и запись данных.')

    parser.add_argument('-sv', '--save', action='store_true', help='Напасть на нейтральный замок')
    parser.add_argument('-cap', '--capture', action='store_true', help='Захватить вражеский замок')
    parser.add_argument('-uc', '--clan', action='store_true', help='Обновить список клана')
    parser.add_argument('-r', '--read', action='store_true', help='Показать список игроков для удаления')
    parser.add_argument('-s', '--set', nargs='*', help='Установить/сбросить(reset) имена для удаления')

    return parser
