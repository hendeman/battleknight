"""
Модуль пакетной обработки HTML-файлов статистики BattleKnight.

Проходит по директории с сохранёнными HTML-страницами профилей,
парсит каждую из них выбранной функцией-парсером и сохраняет
результат в JSON, повторяя структуру входных директорий.

Пример использования:

    from module.data_pars import pars_player
    from tr import process_dir

    process_dir(
        root_dir=r"bk\\statistic\\2026",
        output_dir=r"bk\\statistic\\json_2026",
        parse_func=pars_player,
        max_workers=8,
    )

Особенности:
    - Парсинг выполняется в пуле процессов (ProcessPoolExecutor),
      поэтому передаваемая функция parse_func должна быть
      определена на верхнем уровне импортируемого модуля и быть
      picklable (без lambda и локальных замыканий).
    - JSON сохраняется в кодировке UTF-8 с BOM (utf-8-sig),
      чтобы файлы корректно открывались в Windows-инструментах.
    - Структура подкаталогов внутри root_dir сохраняется
      относительно output_dir.
"""

import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional, Tuple

from bs4 import BeautifulSoup

from module.data_pars import pars_player, parse_profile_tables


# Тип функции-парсера: принимает BeautifulSoup, возвращает словарь
ParseFunc = Callable[[BeautifulSoup], dict]

# Список функций-парсеров
PARSERS = {
    "profile": parse_profile_tables,
    "player": pars_player,
}


def process_file(args: Tuple[str, str, str, ParseFunc]) -> Tuple[str, Path]:
    """
    Обрабатывает один HTML-файл: парсит его и сохраняет результат в JSON.

    :param args: кортеж (html_file, root, out, parse_func), где
        html_file — путь к исходному HTML-файлу;
        root      — корневая директория входных данных (для вычисления
                    относительного пути);
        out       — корневая директория для сохранения JSON;
        parse_func — функция парсинга BeautifulSoup -> dict.
    :return: кортеж (путь к исходному файлу, путь к сохранённому JSON).
    """
    html_file, root, out, parse_func = args
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")
    # data = parse_profile_tables(soup)
    data = parse_func(soup)
    rel_path = Path(html_file).relative_to(root)
    out_path = Path(out) / rel_path.with_suffix(".json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return html_file, out_path


def process_dir(
    root_dir: str,
    output_dir: str,
    parse_func: ParseFunc = pars_player,
    max_workers: Optional[int] = None,
) -> None:
    """
    Рекурсивно обходит root_dir, парсит все *.html и сохраняет JSON
    в output_dir с сохранением относительной структуры каталогов.

    :param root_dir:    директория с исходными HTML-файлами.
    :param output_dir:  директория для сохранения JSON-файлов
                        (создаётся, если не существует).
    :param parse_func:  функция парсинга BeautifulSoup -> dict.
                        Должна быть picklable (определена на верхнем
                        уровне импортируемого модуля). По умолчанию
                        используется pars_player.
    :param max_workers: число процессов в пуле. Если None — значение
                        выбирается ProcessPoolExecutor автоматически
                        (обычно по числу CPU).
    """
    root = Path(root_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    html_files = list(root.rglob("*.html"))

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_file, (str(hf), str(root), str(out), parse_func)
            )
            for hf in html_files
        ]
        for future in as_completed(futures):
            try:
                src, dst = future.result()
                print(f"OK: {src} -> {dst}")
            except Exception as e:
                print(f"FAIL: {e}")


if __name__ == "__main__":
    process_dir(
        r"bk\statistic\2026",
        r"bk\statistic\json_2026",
        parse_func=PARSERS["player"],  # или pars_player
        max_workers=8,
    )