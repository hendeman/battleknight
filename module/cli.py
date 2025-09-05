import argparse


def arg_parser():
    """Настройка парсера аргументов."""
    parser = argparse.ArgumentParser(description='Выбор программы')

    parser.add_argument('-gr', '--group', action='store_true', help='Включить прохождение группы')

    return parser
