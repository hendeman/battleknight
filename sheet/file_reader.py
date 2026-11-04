"""
Кешированное чтение списка ID игроков из локального текстового файла.
Python 3.6 compatible.
"""
import os
from pathlib import Path
from typing import List, Optional


class CachedFileReader(object):
    """Читает ID игроков из файла с кешированием по mtime."""

    def __init__(self, file_path):
        # type: (str) -> None
        current_dir = Path(__file__).parent
        self.file_path = current_dir / file_path   # type: Path
        self._cache = None                         # type: Optional[List[int]]
        self._last_mtime = None                    # type: Optional[float]

    def read_ids(self):
        # type: () -> List[int]
        """Возвращает список ID. Перечитывает файл только при изменении."""
        try:
            current_mtime = os.path.getmtime(str(self.file_path))
        except FileNotFoundError:
            raise FileNotFoundError("Файл {} не найден".format(self.file_path))

        if (
            self._cache is not None
            and self._last_mtime is not None
            and self._last_mtime == current_mtime
        ):
            return self._cache.copy()

        player_ids = []  # type: List[int]
        with open(str(self.file_path), "r", encoding="utf-8-sig") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    player_ids.append(int(line))
                except ValueError:
                    print("Предупреждение: '{}' не является числом и будет пропущено".format(line))

        self._cache = player_ids
        self._last_mtime = current_mtime
        return player_ids.copy()

    def clear_cache(self):
        # type: () -> None
        """Сбросить кеш."""
        self._cache = None
        self._last_mtime = None


if __name__ == "__main__":
    reader = CachedFileReader("id_players.txt")
    print(reader.read_ids())