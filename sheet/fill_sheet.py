"""
Работа с Google Таблицей статистики игроков.

Ключевые принципы:
- Все операции чтения/записи — через SheetLayout (единый кэш структуры).
- Условное форматирование применяется один раз на столбец, а не в цикле.
- Столбцы добавляются/удаляются через insert/deleteDimension — форматы не рушатся.
- Запись новой строки — один batch_update.
- Добавлены ретраи для запросов к Google Sheets API.

Python 3.6 compatible.
"""

import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials

from logs.logs import p_log
from sheet.layout import SheetLayout

from gspread.exceptions import APIError

try:
    from gspread.exceptions import RequestError
except ImportError:
    RequestError = APIError

try:
    from google.auth.exceptions import TransportError
except ImportError:
    TransportError = None


# Логирование — только WARNING, чтобы не забивать память и stdout.
logging.getLogger("gspread").setLevel(logging.WARNING)
logging.getLogger("googleapiclient").setLevel(logging.WARNING)
logging.getLogger("google_auth_httplib2").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("oauth2client").setLevel(logging.WARNING)


CREDENTIALS_FILE = "credentials.json"
SHEET_URL = "https://docs.google.com/spreadsheets/d/18EBB4hdmSRStSpOFhBDoX3Vrg7cZr9sw3jKHz6koBEc/edit"
SHEET_TAB = "pupsiki"

# ------------------------------------------------------------------ #
# Настройки ретраев
# ------------------------------------------------------------------ #
RETRY_ATTEMPTS = 5
RETRY_INITIAL_DELAY = 1.0
RETRY_MAX_DELAY = 60.0
RETRY_BACKOFF_FACTOR = 2.0

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

RETRYABLE_TEXT = (
    "rate limit",
    "ratelimit",
    "too many requests",
    "quota",
    "backend error",
    "internal error",
    "service unavailable",
    "connection reset",
    "connection aborted",
    "timed out",
)


# ------------------------------------------------------------------ #
# Вспомогательные функции ретраев
# ------------------------------------------------------------------ #
def _get_status_code(exc):
    """
    Пытается достать HTTP-статус из исключения.
    """
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status

    status = getattr(exc, "code", None)
    if isinstance(status, int):
        return status

    status = getattr(exc, "status", None)
    if isinstance(status, int):
        return status

    return None


def _get_retry_after(exc):
    """
    Если сервер прислал Retry-After — используем его.
    Поддерживаем только числовое значение.
    """
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None

    try:
        value = headers.get("Retry-After")
    except AttributeError:
        return None

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_retryable_google_error(exc):
    """
    Возвращает True, если ошибку имеет смысл повторить.
    """
    # Сетевые таймауты и обрывы соединения
    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True

    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True

    if TransportError is not None and isinstance(exc, TransportError):
        return True

    status = _get_status_code(exc)

    # 429 / 5xx — почти всегда временно
    if status in RETRYABLE_STATUS_CODES:
        return True

    # Ошибки от gspread / Google API
    if isinstance(exc, (APIError, RequestError)):
        text = str(exc).lower()
        if any(marker in text for marker in RETRYABLE_TEXT):
            return True
        return False

    # Обычные ошибки requests, где статус неясен
    if isinstance(exc, requests.exceptions.RequestException):
        # Если статус неизвестен — чаще всего это сетевой сбой.
        # Если статус есть и он не временный — не повторять.
        return status is None or status in RETRYABLE_STATUS_CODES

    return False


def _execute_with_retry(
    func,
    args,
    kwargs,
    attempts,
    initial_delay,
    max_delay,
    backoff_factor
):
    """
    Внутренний исполнитель ретраев.
    """
    attempts = max(1, int(attempts))
    delay = float(initial_delay)
    name = getattr(func, "__name__", str(func))

    for attempt in range(1, attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if attempt >= attempts or not _is_retryable_google_error(exc):
                raise

            retry_after = _get_retry_after(exc)
            if retry_after is not None:
                sleep_for = min(float(retry_after), float(max_delay))
            else:
                # экспоненциальная задержка + дрожание
                sleep_for = min(
                    float(max_delay),
                    delay / 2.0 + random.uniform(0.0, delay / 2.0)
                )

            p_log(
                "⏳ Retry Google Sheets '{}': попытка {}/{}. Ошибка: {}. Сон {:.2f} сек.".format(
                    name,
                    attempt,
                    attempts,
                    exc,
                    sleep_for
                )
            )

            time.sleep(sleep_for)
            delay = min(float(max_delay), delay * float(backoff_factor))

    # Сюда в норме не попадаем.
    raise RuntimeError("Retry loop finished without result")


# ------------------------------------------------------------------ #
# Константы форматирования
# ------------------------------------------------------------------ #
# ВАЖНО: ключи должны быть без пробелов: red, green, blue.
RED_LIGHT = {"red": 1.0, "green": 0.8, "blue": 0.8}
GREEN_LIGHT = {"red": 0.8, "green": 1.0, "blue": 0.8}
GREEN_DARK = {"red": 0.2, "green": 0.8, "blue": 0.6}

HEADER_ROW_1 = 0          # индекс строки 1 (0-based)
HEADER_ROW_2 = 1          # индекс строки 2 (0-based)
FIRST_DATA_ROW = 2        # 3-я строка — первая с данными


class PlayerStatsSheet(object):
    """Обёртка над gspread-листом для хранения статистики игроков."""

    def __init__(
        self,
        credentials_file,
        sheet_url_or_id,
        sheet_name="test",
        max_rows=150,
        auto_format=True,
        clear_every=0,
    ):
        # type: (str, str, str, int, bool, int) -> None
        current_dir = Path(__file__).parent
        self.credentials_file = current_dir / credentials_file
        self.sheet_url_or_id = sheet_url_or_id
        self.sheet_name = sheet_name
        self.max_rows = max_rows
        self.auto_format = auto_format
        self.clear_every = clear_every
        self.cache_file = current_dir / "last_clear_cache.json"

        if not self.credentials_file.exists():
            raise FileNotFoundError(
                "Файл {} не найден. Ожидался в: {}".format(
                    self.credentials_file, current_dir
                )
            )

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]

        creds = ServiceAccountCredentials.from_json_keyfile_name(
            str(self.credentials_file), scope
        )

        self.client = gspread.authorize(creds)
        self.client.set_timeout(60)

        self._open_spreadsheet()

        # Кэш структуры
        self.layout = SheetLayout()

        # Столбцы, для которых уже создано правило форматирования (id игрока)
        self._formatted_players = set()   # type: Set[int]

        if self.auto_format:
            self._set_alignment_for_all_cells()
            self.ensure_headers()
            self.format_header()
            self.freeze_header_rows(2)    # закрепить строки 1–2

        # Восстанавливаем layout из таблицы
        self._reload_layout_from_sheet()
        self._formatted_players = self._fetch_existing_format_columns()

    # ------------------------------------------------------------------ #
    # Универсальная обёртка для ретраев
    # ------------------------------------------------------------------ #
    def _g(self, func, *args, **kwargs):
        """
        Обёртка над _execute_with_retry для повторных попыток запросов к Google Sheets.

        Использование:
            self._g(self.worksheet.row_values, 1)
            self._g(self.spreadsheet.batch_update, {"requests": [...]})
        """
        return _execute_with_retry(
            func,
            args,
            kwargs,
            RETRY_ATTEMPTS,
            RETRY_INITIAL_DELAY,
            RETRY_MAX_DELAY,
            RETRY_BACKOFF_FACTOR
        )

    # ------------------------------------------------------------------ #
    # Открытие/инициализация
    # ------------------------------------------------------------------ #
    def _open_spreadsheet(self):
        # type: () -> None
        if "http" in self.sheet_url_or_id:
            self.spreadsheet = self._g(self.client.open_by_url, self.sheet_url_or_id)
        else:
            self.spreadsheet = self._g(self.client.open_by_key, self.sheet_url_or_id)

        try:
            self.worksheet = self._g(self.spreadsheet.worksheet, self.sheet_name)
            p_log("✅ Открыта вкладка '{}'".format(self.sheet_name))
        except gspread.exceptions.WorksheetNotFound:
            self.worksheet = self._g(
                self.spreadsheet.add_worksheet,
                title=self.sheet_name,
                rows=self.max_rows + 10,
                cols=100
            )
            p_log("✅ Создана вкладка '{}'".format(self.sheet_name))

    def ensure_headers(self):
        # type: () -> None
        """Гарантирует, что A1='ID' и A2='время | имя'."""
        a1 = self._g(self.worksheet.acell, "A1").value
        if not a1:
            self._g(self.worksheet.update_cell, 1, 1, "ID")

        a2 = self._g(self.worksheet.acell, "A2").value
        if not a2:
            self._g(self.worksheet.update_cell, 2, 1, "время | имя")

    def freeze_header_rows(self, count=2):
        # type: (int) -> None
        """
        Закрепляет первые `count` строк сверху.
        Google Sheets: gridProperties.frozenRowCount.
        """
        try:
            body = {
                "requests": [{
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": self.worksheet.id,
                            "gridProperties": {
                                "frozenRowCount": int(count),
                            },
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                }]
            }
            self._g(self.spreadsheet.batch_update, body)
            p_log("📌 Закреплено {} строк(и) сверху".format(count))
        except Exception as e:
            p_log("⚠️ Не удалось закрепить строки: {}".format(e))

    def format_header(self):
        # type: () -> None
        """
        Жирный шрифт + фон + выравнивание для строк 1–2.
        Диапазон столбцов берём по фактическому размеру таблицы
        (строки 1 и 2), а не только по layout.
        """
        row1 = self._g(self.worksheet.row_values, 1) or []
        row2 = self._g(self.worksheet.row_values, 2) or []

        try:
            total_cols = self.worksheet.col_count
        except Exception:
            total_cols = 0

        last_col = max(
            len(row1),
            len(row2),
            len(self.layout.expected_row1),
            len(self.layout.expected_row2),
            10,
        )

        if total_cols:
            last_col = min(last_col, total_cols)

        sheet_id = self.worksheet.id

        requests = [{
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": HEADER_ROW_1,
                    "endRowIndex": HEADER_ROW_2 + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": last_col,
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {"bold": True, "fontSize": 11},
                        "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
                    }
                },
                "fields": (
                    "userEnteredFormat(horizontalAlignment,verticalAlignment,"
                    "textFormat,backgroundColor)"
                ),
            }
        }]

        try:
            self._g(self.spreadsheet.batch_update, {"requests": requests})
        except Exception as e:
            p_log("⚠️ Не удалось отформатировать заголовок: {}".format(e))

    def _set_alignment_for_all_cells(self):
        # type: () -> None
        """Центрирование по всему листу — один раз при инициализации."""
        requests = [{
            "repeatCell": {
                "range": {"sheetId": self.worksheet.id},
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment)",
            }
        }]

        try:
            self._g(self.spreadsheet.batch_update, {"requests": requests})
        except Exception as e:
            p_log("⚠️ Не удалось установить выравнивание: {}".format(e))

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _reload_layout_from_sheet(self):
        # type: () -> None
        """Считывает строки 1–2 и восстанавливает SheetLayout."""
        row1 = self._g(self.worksheet.row_values, 1) or []
        row2 = self._g(self.worksheet.row_values, 2) or []

        ids = []      # type: List[int]
        names = {}    # type: Dict[int, str]

        for idx, raw in enumerate(row1):
            if idx == 0:
                continue  # "ID"

            try:
                pid = int(raw)
            except (ValueError, TypeError):
                continue

            ids.append(pid)

            if idx < len(row2):
                names[pid] = row2[idx]

        self.layout.ids = ids
        self.layout.names = names

    def _fetch_existing_format_columns(self):
        # type: () -> Set[int]
        """
        Возвращает id игроков, для столбцов которых уже есть правила
        условного форматирования. Нужно, чтобы не дублировать правила.
        """
        try:
            metadata = self._g(self.spreadsheet.fetch_sheet_metadata)
        except Exception:
            return set()

        formatted = set()   # type: Set[int]

        for sheet in metadata.get("sheets", []):
            if sheet["properties"]["sheetId"] != self.worksheet.id:
                continue

            for rule in sheet.get("conditionalFormats", []):
                for rng in rule.get("ranges", []):
                    col0 = rng.get("startColumnIndex", -1)
                    if col0 < 0:
                        continue

                    if col0 - 1 < len(self.layout.ids):
                        formatted.add(self.layout.ids[col0 - 1])

            break

        return formatted

    def _get_conditional_format_rules(self):
        # type: () -> List[dict]
        """
        Возвращает список словарей {'index': int, 'start_col': int, 'end_col': int}
        для текущего листа. Индекс — позиция правила в списке листа (0-based).
        """
        try:
            metadata = self._g(self.spreadsheet.fetch_sheet_metadata)
        except Exception as e:
            p_log("⚠️ Не удалось получить metadata: {}".format(e))
            return []

        result = []

        for sheet in metadata.get("sheets", []):
            if sheet["properties"]["sheetId"] != self.worksheet.id:
                continue

            for idx, rule in enumerate(sheet.get("conditionalFormats", [])):
                for rng in rule.get("ranges", []):
                    result.append({
                        "index": idx,
                        "start_col": rng.get("startColumnIndex", -1),
                        "end_col": rng.get("endColumnIndex", -1),
                    })

            break

        return result

    def _delete_rules_for_column(self, col_1based):
        # type: (int) -> None
        """
        Удаляет все условные правила, диапазон которых начинается с указанного
        столбца (1-based).
        """
        col0 = col_1based - 1
        rules = self._get_conditional_format_rules()

        to_delete = sorted(
            {r["index"] for r in rules if r["start_col"] == col0},
            reverse=True,
        )

        if not to_delete:
            return

        requests = []

        for idx in to_delete:
            requests.append({
                "deleteConditionalFormatRule": {
                    "sheetId": self.worksheet.id,
                    "index": idx,
                }
            })

        try:
            self._g(self.spreadsheet.batch_update, {"requests": requests})
            p_log("  🧹 Удалено {} правил форматирования для col {}".format(
                len(to_delete), col_1based
            ))
        except Exception as e:
            p_log("⚠️ Не удалось удалить правила для col {}: {}".format(col_1based, e))

    def sync_layout(self, current_ids):
        # type: (List[int]) -> None
        """
        Приводит структуру таблицы в соответствие с current_ids:
        - добавляет недостающие столбцы,
        - удаляет лишние,
        - обновляет кэш layout.

        Имена существующих игроков не перезаписываются.
        """
        actual_row1 = self._g(self.worksheet.row_values, 1) or ["ID"]

        actual_ids = []   # type: List[int]
        for h in actual_row1[1:]:
            try:
                actual_ids.append(int(h))
            except (ValueError, TypeError):
                pass

        expected_set = set(current_ids)
        actual_set = set(actual_ids)

        to_remove = [i for i in actual_ids if i not in expected_set]
        to_add = [i for i in current_ids if i not in actual_set]

        # 1. Удаляем лишние столбцы справа налево
        to_remove_sorted = sorted(
            to_remove, key=lambda p: actual_ids.index(p), reverse=True
        )

        for pid in to_remove_sorted:
            col = actual_ids.index(pid) + 2  # 1-based, +1 за 'ID'

            # ← снести правила этого столбца
            self._delete_rules_for_column(col)

            try:
                self._g(self.worksheet.delete_columns, col)
                p_log("  🗑 Удалён столбец игрока {}".format(pid))
            except Exception as e:
                p_log("⚠️ Не удалось удалить столбец {}: {}".format(pid, e))

            # ← игрок ушёл — правило больше не актуально
            self._formatted_players.discard(pid)

        # 2. Добавляем недостающие
        for pid in to_add:
            try:
                self._g(self.worksheet.add_cols, 1)
                new_col = len(self._g(self.worksheet.row_values, 1)) + 1
                self._g(self.worksheet.update_cell, 1, new_col, str(pid))
                p_log("  ➕ Добавлен столбец игрока {}".format(pid))
            except Exception as e:
                p_log("⚠️ Не удалось добавить столбец {}: {}".format(pid, e))

        # 3. Обновляем кэш
        self._reload_layout_from_sheet()

        # 4. Расширяем/перерисовываем шапку под новое число столбцов
        if self.auto_format:
            self.format_header()

    def update_names(self, names):
        # type: (Dict[int, str]) -> None
        """
        Обновляет строку 2 для новых игроков. Существующие имена НЕ трогает
        (требование #5), но заполняет пустые ячейки.
        """
        row2 = self._g(self.worksheet.row_values, 2) or []
        updates = []   # type: List[dict]

        for idx, pid in enumerate(self.layout.ids):
            col = idx + 2  # 1-based
            current_name = row2[idx + 1] if idx + 1 < len(row2) else ""
            new_name = names.get(pid)

            if new_name and not current_name:
                updates.append({
                    "range": gspread.utils.rowcol_to_a1(2, col),
                    "values": [[new_name]],
                })
                self.layout.names[pid] = new_name

        if updates:
            try:
                self._g(self.worksheet.batch_update, updates)
                p_log("  ✏️ Обновлены имена для {} игроков".format(len(updates)))
            except Exception as e:
                p_log("⚠️ Не удалось обновить имена: {}".format(e))

    # ------------------------------------------------------------------ #
    # Условное форматирование — идемпотентное, один раз на столбец
    # ------------------------------------------------------------------ #
    def ensure_conditional_format(self, player_id):
        # type: (int) -> None
        """
        Создаёт правила форматирования для столбца игрока, если их ещё нет.

        Правило 1 (градиент):  0     -> 1000   (светло-красный -> светло-зелёный)
        Правило 2 (градиент):  1000  -> MAX    (светло-зелёный -> насыщенный зелёный)

        Диапазон без endRowIndex — автоматически расширяется на новые строки.
        """
        if player_id in self._formatted_players:
            return

        col = self.layout.column_of(player_id)
        if col is None:
            return

        # ← страховка от ручных правок в UI
        existing = self._get_conditional_format_rules()
        if any(r["start_col"] == col - 1 for r in existing):
            self._formatted_players.add(player_id)
            return

        sheet_id = self.worksheet.id

        rng = {
            "sheetId": sheet_id,
            "startRowIndex": FIRST_DATA_ROW,   # с 3-й строки
            "startColumnIndex": col - 1,       # 0-based
            "endColumnIndex": col,             # одна колонка
            # endRowIndex не задаём -> до конца листа
        }

        requests = [
            # Правило 1: 0 -> 1000, светло-красный -> светло-зелёный
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [rng],
                        "gradientRule": {
                            "minpoint": {
                                "type": "NUMBER",
                                "value": "0",
                                "color": RED_LIGHT,
                            },
                            "maxpoint": {
                                "type": "NUMBER",
                                "value": "1000",
                                "color": GREEN_LIGHT,
                            },
                        },
                    },
                    "index": 2,
                }
            },
            # Правило 2: 1000 -> MAX, светло-зелёный -> насыщенный зелёный
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [rng],
                        "gradientRule": {
                            "minpoint": {
                                "type": "NUMBER",
                                "value": "1000",
                                "color": GREEN_LIGHT,
                            },
                            "maxpoint": {
                                "type": "MAX",
                                "color": GREEN_DARK,
                            },
                        },
                    },
                    "index": 1,
                }
            },
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [rng],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_EQ",
                                "values": [
                                    {
                                        "userEnteredValue": "0"
                                    }
                                ]
                            },
                            "format": {
                                "backgroundColor": RED_LIGHT
                            }
                        }
                    },
                    "index": 0,
                }
            }
        ]

        try:
            self._g(self.spreadsheet.batch_update, {"requests": requests})
            self._formatted_players.add(player_id)
            p_log("  🎨 Форматирование создано для игрока {} (col {})".format(player_id, col))
        except Exception as e:
            p_log("⚠️ Ошибка форматирования {}: {}".format(player_id, e))

    # ------------------------------------------------------------------ #
    # Запись данных
    # ------------------------------------------------------------------ #
    def _build_cell(self, value):
        # type: (object) -> dict
        """Формирует userEnteredValue для updateCells."""
        if value is None or value == "":
            return {}

        if isinstance(value, str):
            return {"userEnteredValue": {"stringValue": value}}

        try:
            return {"userEnteredValue": {"numberValue": float(value)}}
        except (ValueError, TypeError):
            return {"userEnteredValue": {"stringValue": str(value)}}

    def add_record(self, changes):
        # type: (Dict[int, object]) -> bool
        """
        Добавляет новую строку с данными в позицию 3.

        changes: {player_id: PlayerStats с полем difference_loot}
        """
        if not changes:
            p_log("changes пуст — пропускаем")
            return True

        # 1. Очистка по расписанию
        if self.clear_every and self._should_clear_table():
            self._clear_table()

        # 2. Формируем строку
        now = datetime.now().strftime("%d.%m %H:%M")
        row_values = [now]   # type: List[object]

        for pid in self.layout.ids:
            player = changes.get(pid)
            if player is not None and getattr(player, "difference_loot", None) is not None:
                row_values.append(player.difference_loot)
            else:
                row_values.append("")

        # 3. Один batch: вставка строки 3 + запись данных
        sheet_id = self.worksheet.id
        num_cols = len(row_values)

        requests = [
            {
                "insertRange": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": FIRST_DATA_ROW,
                        "endRowIndex": FIRST_DATA_ROW + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": num_cols,
                    },
                    "shiftDimension": "ROWS",
                }
            },
            {
                "updateCells": {
                    "start": {
                        "sheetId": sheet_id,
                        "rowIndex": FIRST_DATA_ROW,
                        "columnIndex": 0,
                    },
                    "rows": [{
                        "values": [self._build_cell(v) for v in row_values]
                    }],
                    "fields": "userEnteredValue",
                }
            },
        ]

        try:
            self._g(self.spreadsheet.batch_update, {"requests": requests})
            p_log("📝 Добавлена строка: {}".format(row_values))
        except Exception as e:
            p_log("❌ Ошибка вставки строки: {}".format(e))
            return False

        # 4. Обрезаем хвост, если превысили лимит
        try:
            self._trim_rows()
        except Exception as e:
            p_log("⚠️ Ошибка обрезки старых строк после вставки: {}".format(e))

        return True

    def _trim_rows(self):
        # type: () -> None
        """Удаляет самые старые строки, если их больше max_rows."""
        data_rows = self.get_data_rows_count()
        if data_rows <= self.max_rows:
            return

        rows_to_delete = data_rows - self.max_rows
        last_data_row = FIRST_DATA_ROW + data_rows          # 1-based последняя
        first_delete = last_data_row - rows_to_delete + 1

        try:
            self._g(self.worksheet.delete_rows, first_delete, last_data_row)
            p_log("🗑 Удалено {} старых строк".format(rows_to_delete))
        except Exception as e:
            p_log("⚠️ Ошибка удаления старых строк: {}".format(e))

    # ------------------------------------------------------------------ #
    # Вспомогательные методы
    # ------------------------------------------------------------------ #
    def get_data_rows_count(self):
        # type: () -> int
        """Количество заполненных строк с данными (без шапки)."""
        all_data = self._g(self.worksheet.get_all_values)

        if len(all_data) <= 2:
            return 0

        count = 0
        for row in all_data[2:]:
            if any(cell != "" for cell in row):
                count += 1
            else:
                break

        return count

    def show_current_state(self):
        # type: () -> None
        try:
            all_data = self._g(self.worksheet.get_all_values)

            p_log("=" * 80)
            p_log("ТЕКУЩЕЕ СОСТОЯНИЕ ТАБЛИЦЫ")
            p_log("=" * 80)

            if not all_data:
                p_log("Таблица пуста")
            else:
                p_log("Строка 1: {}".format(all_data[0] if len(all_data) > 0 else []))
                p_log("Строка 2: {}".format(all_data[1] if len(all_data) > 1 else []))
                p_log("Строк с данными: {}".format(max(0, len(all_data) - 2)))

                for i, row in enumerate(all_data[2:7], 1):
                    p_log("  {}. {}".format(i, row))

            p_log("=" * 80)
        except Exception as e:
            p_log("❌ Ошибка отображения: {}".format(e))

    def hide_line(self, start_index, end_index):
        # type: (int, int) -> None
        body = {
            "requests": [{
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": self.worksheet.id,
                        "dimension": "ROWS",
                        "startIndex": start_index - 1,
                        "endIndex": end_index - 1,
                    },
                    "properties": {"hiddenByUser": True},
                    "fields": "hiddenByUser",
                }
            }]
        }

        try:
            self._g(self.spreadsheet.batch_update, body)
        except Exception as e:
            p_log("⚠️ Не удалось скрыть строки {}-{}: {}".format(start_index, end_index, e))

    # ------------------------------------------------------------------ #
    # Очистка по расписанию
    # ------------------------------------------------------------------ #
    def _get_last_clear_date(self):
        # type: () -> Optional[datetime]
        try:
            if self.cache_file.exists():
                with open(str(self.cache_file), "r") as f:
                    data = json.load(f)
                    last = data.get("last_clear_date")

                    if last:
                        try:
                            return datetime.strptime(last, "%Y-%m-%dT%H:%M:%S.%f")
                        except ValueError:
                            return datetime.strptime(last, "%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            p_log("⚠️ Ошибка чтения кэша: {}".format(e))

        return None

    def _save_last_clear_date(self, date):
        # type: (datetime) -> None
        try:
            with open(str(self.cache_file), "w") as f:
                json.dump({
                    "last_clear_date": date.isoformat(),
                    "sheet_id": self.spreadsheet.id,
                    "worksheet_id": self.worksheet.id,
                }, f, indent=2)
        except Exception as e:
            p_log("⚠️ Ошибка сохранения кэша: {}".format(e))

    def _should_clear_table(self):
        # type: () -> bool
        last = self._get_last_clear_date()
        if last is None:
            return True

        next_clear = datetime(last.year, last.month, last.day) + timedelta(days=self.clear_every)
        return datetime.now() >= next_clear

    def _clear_table(self):
        # type: () -> bool
        try:
            p_log("🧹 Очистка таблицы по расписанию")

            total = self.worksheet.row_count
            if total > 2:
                self._g(self.worksheet.delete_rows, 3, total)

            self.ensure_headers()
            self._save_last_clear_date(datetime.now())
            return True
        except Exception as e:
            p_log("❌ Ошибка очистки: {}".format(e))
            return False

    def force_clear_table(self):
        # type: () -> bool
        return self._clear_table()

    def get_last_clear_info(self):
        # type: () -> Optional[datetime]
        return self._get_last_clear_date()


# ------------------------------------------------------------------ #
# Ручной запуск
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    sheet = PlayerStatsSheet(CREDENTIALS_FILE, SHEET_URL, SHEET_TAB)
    sheet.show_current_state()