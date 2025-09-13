from pathlib import Path
from logs.logs import p_log, setup_logging
from module.cli import arg_parser
from module.all_function import read_pickle_file, create_pickle_file, change_pickle_file
from setting import DIRECTORY_PICKLES, EXTENSION_PICKLES


def get_file_path(filename: str) -> Path:
    """Создает полный путь к файлу."""
    return Path(DIRECTORY_PICKLES) / f"{filename}{EXTENSION_PICKLES}"


def handle_read_pickle(filename: str) -> None:
    """Обработчик чтения pickle-файла."""
    path_file = get_file_path(filename)
    p_log(f"Чтение файла: '{path_file}'")
    read_pickle_file(name_file=str(path_file))


def handle_create_pickle(filename: str) -> None:
    """Обработчик создания pickle-файла."""
    path_file = get_file_path(filename)
    p_log(f"Создание файла: '{path_file}'")
    create_pickle_file(name_file=str(path_file))


def handle_change_pickle(filename: str) -> None:
    """Обработчик изменения pickle-файла."""
    path_file = get_file_path(filename)
    p_log(f"Изменение файла: '{path_file}'")
    change_pickle_file(name_file=str(path_file))


def main() -> None:
    """Основная функция приложения."""
    setup_logging()
    parser = arg_parser()
    args = parser.parse_args()

    # Обработка аргументов
    if args.read_pickle:
        handle_read_pickle(args.read_pickle)

    if args.create_pickle:
        handle_create_pickle(args.create_pickle)

    if args.change_pickle:
        handle_change_pickle(args.change_pickle)

    # Если не передано ни одного аргумента
    if not any([args.read_pickle, args.create_pickle, args.change_pickle]):
        parser.print_help(filter_group='pickle')


if __name__ == "__main__":
    main()
