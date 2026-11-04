"""
Кэш структуры таблицы: единый источник правды о соответствии
id игрока <-> индекс столбца и id <-> имя.

Все операции записи/форматирования работают через этот объект,
чтобы не читать таблицу лишний раз.

Python 3.6 compatible (без dataclasses).
"""
from typing import Dict, List, Optional


class SheetLayout(object):
    """Структура листа: порядок ID и соответствующие им имена."""

    def __init__(self, ids=None, names=None):
        # type: (Optional[List[int]], Optional[Dict[int, str]]) -> None
        # Порядок столбцов с игроками (слева направо, без учёта "ID")
        self.ids = list(ids) if ids else []
        # id -> имя (из строки 2). Имена только читаются, не перезаписываются.
        self.names = dict(names) if names else {}

    def column_of(self, player_id):
        # type: (int) -> Optional[int]
        """
        1-based индекс столбца для игрока.
        Столбец 1 — 'ID', столбец 2 — первый игрок и т.д.
        Возвращает None, если игрока нет в layout.
        """
        try:
            return self.ids.index(player_id) + 2
        except ValueError:
            return None

    def index_of(self, player_id):
        # type: (int) -> Optional[int]
        """0-based позиция игрока в списке ids."""
        try:
            return self.ids.index(player_id)
        except ValueError:
            return None

    @property
    def expected_row1(self):
        # type: () -> List[str]
        """Ожидаемая строка 1 (ID игроков)."""
        return ["ID"] + [str(i) for i in self.ids]

    @property
    def expected_row2(self):
        # type: () -> List[str]
        """Ожидаемая строка 2 (имена игроков)."""
        return ["время | имя"] + [self.names.get(i, "") for i in self.ids]

    def diff(self, actual_ids):
        # type: (List[int]) -> Dict[str, List[int]]
        """
        Что нужно добавить/удалить, чтобы layout совпал с actual_ids
        (актуальный список из файла id_players.txt).
        """
        actual_set = set(actual_ids)
        expected_set = set(self.ids)
        return {
            "to_add": [i for i in actual_ids if i not in expected_set],
            "to_remove": [i for i in self.ids if i not in actual_set],
        }

    def rebuild(self, player_ids, names):
        # type: (List[int], Dict[int, str]) -> None
        """Полностью пересобрать layout из списка ID и словаря имён."""
        self.ids = list(player_ids)
        self.names = {
            pid: names.get(pid, self.names.get(pid, ""))
            for pid in player_ids
        }