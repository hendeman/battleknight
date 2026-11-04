# sheet/custom_sheet.py
# -*- coding: utf-8 -*-

"""
CustomStatsSheet

Заполнение произвольной вкладки без обязательной записи заголовка.
Заголовок пользователь может сделать сам.

Возможности:
- запись данных с нужной строки через start_row;
- замена первой строки, если передан список через first_row;
- статическая покраска строк по маркеру, например "[SLAVS]";
- сортировка указанного диапазона данных по столбцу;
- безопасная очистка строк даже при замороженных строках;
- удаление пустых столбцов;
- удаление всех правил условного форматирования при заполнении;
- градиентное условное форматирование столбцов:
    * red_to_green: минимум красный, максимум зелёный;
    * green_to_red: минимум зелёный, максимум красный;
- выравнивание столбцов данных через аргумент alignments.
"""

try:
    from .fill_sheet import PlayerStatsSheet
except ImportError:
    from sheet.fill_sheet import PlayerStatsSheet

try:
    from logs.logs import p_log
except ImportError:
    def p_log(message):
        print(message)


DEFAULT_MARKER_COLOR = {
    "red": 1.0,
    "green": 0.8,
    "blue": 0.8,
}

WHITE_COLOR = {
    "red": 1.0,
    "green": 1.0,
    "blue": 1.0,
}

GRADIENT_RED = {
    "red": 1.0,
    "green": 0.7,
    "blue": 0.7,
}

GRADIENT_GREEN = {
    "red": 0.7,
    "green": 1.0,
    "blue": 0.7,
}

GRADIENT_MODE_RED_TO_GREEN = "red_to_green"
GRADIENT_MODE_GREEN_TO_RED = "green_to_red"


def _normalize_color(color):
    """
    Приводит цвет к корректному виду для Google Sheets API.

    Корректные ключи:
        red, green, blue

    Метод дополнительно страхует от вариантов с пробелами:
        {"red ": 1.0, "green ": 0.8, "blue ": 0.8}
    """
    if not color or not isinstance(color, dict):
        return dict(DEFAULT_MARKER_COLOR)

    normalized = {}

    for raw_key, raw_value in color.items():
        key = str(raw_key).strip().lower()

        try:
            normalized[key] = float(raw_value)
        except (TypeError, ValueError):
            normalized[key] = 0.0

    result = {}

    for key in ("red", "green", "blue"):
        value = normalized.get(key, 0.0)

        if value < 0.0:
            value = 0.0

        if value > 1.0:
            value = 1.0

        result[key] = value

    return result


class CustomStatsSheet(PlayerStatsSheet):
    """
    Наследник PlayerStatsSheet для произвольных таблиц.

    Рекомендуется использовать с auto_format=False:

        sheet = CustomStatsSheet(
            credentials_file=CREDENTIALS_FILE,
            sheet_url_or_id=SHEET_URL,
            sheet_name="my_tab",
            auto_format=False,
        )
    """

    # ------------------------------------------------------------------ #
    # Подготовка данных
    # ------------------------------------------------------------------ #

    def _prepare_rows(self, rows):
        """
        Приводит строки к списку списков.
        """
        result = []

        for row in rows or []:
            if row is None:
                result.append([])
            elif isinstance(row, (list, tuple)):
                result.append(list(row))
            else:
                result.append([row])

        return result

    def _prepare_first_row(self, first_row):
        """
        Если first_row является списком или кортежем, возвращает список.
        Иначе возвращает None — значит первую строку не трогаем.
        """
        if first_row is None:
            return None

        if isinstance(first_row, (list, tuple)):
            return list(first_row)

        return None

    # ------------------------------------------------------------------ #
    # Работа со столбцами
    # ------------------------------------------------------------------ #

    def _column_to_0based(self, col):
        """
        Преобразует столбец к 0-based индексу для Google Sheets API.

        Рекомендуемый способ передачи столбца — буква:
            "A", "B", "D", "AA"

        Также поддерживается int:
            0 -> A
            1 -> B
            2 -> C
            3 -> D

        Строки вида "$D", "D2", "d" тоже поддерживаются.
        """
        if col is None:
            return None

        if isinstance(col, int):
            if col < 0:
                return None
            return col

        if isinstance(col, float):
            col_int = int(col)
            if col_int < 0:
                return None
            return col_int

        text = str(col).strip().upper().replace("$", "")

        if not text:
            return None

        # Оставляем только буквы.
        # Это позволяет передавать "D", "d", "$D", "D2".
        letters = "".join(ch for ch in text if ch.isalpha())

        if not letters:
            return None

        index = 0

        for ch in letters:
            if "A" <= ch <= "Z":
                index = index * 26 + (ord(ch) - ord("A") + 1)

        if index <= 0:
            return None

        return index - 1

    def _flatten_columns(self, *column_lists):
        """
        Собирает столбцы из разных форматов в один плоский список.

        Поддерживаются:
            - "A"
            - ["A", "B"]
            - ("A", "B")
            - "A, B, C"
            - [ "A", "B,C" ]
            - 0, 1, 2
        """
        flat = []

        def _add(item):
            if item is None:
                return

            if isinstance(item, (list, tuple, set)):
                for sub in item:
                    _add(sub)
                return

            if isinstance(item, str):
                if "," in item:
                    for part in item.split(","):
                        part = part.strip()
                        if part:
                            flat.append(part)
                else:
                    item = item.strip()
                    if item:
                        flat.append(item)
                return

            flat.append(item)

        for columns in column_lists:
            _add(columns)

        return flat

    def _columns_to_0based_list(self, columns):
        """
        Возвращает список уникальных 0-based индексов столбцов.
        """
        flat = self._flatten_columns(columns)
        result = []

        for col in flat:
            col0 = self._column_to_0based(col)

            if col0 is None:
                continue

            if col0 < 0:
                continue

            if col0 not in result:
                result.append(col0)

        return sorted(result)

    def _resolve_total_cols(
        self,
        rows=None,
        total_cols=None,
        sort_col=None,
        marker_col=None,
        first_row=None,
        extra_columns=None,
    ):
        """
        Определяет количество столбцов, которые нужно использовать
        для записи, сортировки, покраски и условного форматирования.
        """
        total = 0

        if total_cols is not None:
            try:
                total = max(total, int(total_cols))
            except (TypeError, ValueError):
                pass

        if rows:
            for row in rows:
                total = max(total, len(row))

        if first_row is not None:
            total = max(total, len(first_row))

        if sort_col is not None:
            sort_col_0 = self._column_to_0based(sort_col)
            if sort_col_0 is not None:
                total = max(total, sort_col_0 + 1)

        if marker_col is not None:
            marker_col_0 = self._column_to_0based(marker_col)
            if marker_col_0 is not None:
                total = max(total, marker_col_0 + 1)

        if extra_columns is not None:
            for col0 in self._columns_to_0based_list(extra_columns):
                total = max(total, col0 + 1)

        return total

    # ------------------------------------------------------------------ #
    # Выравнивание
    # ------------------------------------------------------------------ #

    def _normalize_horizontal(self, value):
        """
        Приводит значение к горизонтальному выравниванию
        для Google Sheets API.
        """
        if value is None:
            return None

        text = str(value).strip().lower()

        if not text:
            return None

        mapping = {
            "left": "LEFT",
            "l": "LEFT",
            "right": "RIGHT",
            "r": "RIGHT",
            "center": "CENTER",
            "centre": "CENTER",
            "middle": "CENTER",
            "c": "CENTER",
            "m": "CENTER",
            "centered": "CENTER",
            "centred": "CENTER",
        }

        return mapping.get(text)

    def _normalize_vertical(self, value):
        """
        Приводит значение к вертикальному выравниванию
        для Google Sheets API.
        """
        if value is None:
            return None

        text = str(value).strip().lower()

        if not text:
            return None

        mapping = {
            "top": "TOP",
            "t": "TOP",
            "middle": "MIDDLE",
            "m": "MIDDLE",
            "bottom": "BOTTOM",
            "b": "BOTTOM",
            "vmiddle": "MIDDLE",
            "v_middle": "MIDDLE",
        }

        return mapping.get(text)

    def _normalize_alignment_value(self, value):
        """
        Приводит значение выравнивания к словарю для userEnteredFormat.

        Поддерживаются простые строки:
            "left"
            "right"
            "center"
            "middle"

        А также словарь:
            {
                "horizontal": "left",
                "vertical": "middle",
            }
        """
        if value is None:
            return {}

        if isinstance(value, dict):
            result = {}

            horizontal = (
                value.get("horizontal")
                or value.get("h")
                or value.get("horiz")
            )

            vertical = (
                value.get("vertical")
                or value.get("v")
                or value.get("vert")
            )

            if horizontal is not None:
                h = self._normalize_horizontal(horizontal)
                if h:
                    result["horizontalAlignment"] = h

            if vertical is not None:
                v = self._normalize_vertical(vertical)
                if v:
                    result["verticalAlignment"] = v

            return result

        text = str(value).strip().lower()

        if not text:
            return {}

        # Если явно попросили только вертикальное выравнивание.
        if text in ("vmiddle", "v_middle", "vertical_middle"):
            return {"verticalAlignment": "MIDDLE"}

        if text in ("top", "t", "bottom", "b"):
            v = self._normalize_vertical(text)
            if v:
                return {"verticalAlignment": v}
            return {}

        # Простые строки считаем горизонтальным выравниванием.
        # "middle" дополнительно ставим и как вертикальный MIDDLE.
        h = self._normalize_horizontal(text)

        if not h:
            return {}

        result = {
            "horizontalAlignment": h,
        }

        if text in ("middle", "m"):
            result["verticalAlignment"] = "MIDDLE"

        return result

    def _alignment_requests(self, alignments, start_row, rows_count):
        """
        Создаёт запросы выравнивания для столбцов данных.

        alignments:
            {
                "A": "middle",
                "B": "left",
                "C": "right",
            }

        Применяется только к строкам данных, начиная с start_row.
        """
        if not isinstance(alignments, dict):
            return []

        try:
            rows_count = int(rows_count)
            start_row = int(start_row)
        except (TypeError, ValueError):
            return []

        if rows_count <= 0:
            return []

        start_index = start_row - 1
        end_index = start_index + rows_count

        requests = []

        for column_name, alignment_value in alignments.items():
            col0 = self._column_to_0based(column_name)

            if col0 is None:
                p_log(
                    "⚠️ Не удалось распознать столбец выравнивания: {}".format(
                        column_name
                    )
                )
                continue

            if col0 < 0:
                continue

            cell_format = self._normalize_alignment_value(alignment_value)

            if not cell_format:
                p_log(
                    "⚠️ Не удалось распознать выравнивание '{}' для столбца '{}'".format(
                        alignment_value,
                        column_name,
                    )
                )
                continue

            field_names = []

            if "horizontalAlignment" in cell_format:
                field_names.append("horizontalAlignment")

            if "verticalAlignment" in cell_format:
                field_names.append("verticalAlignment")

            if not field_names:
                continue

            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": self.worksheet.id,
                        "startRowIndex": start_index,
                        "endRowIndex": end_index,
                        "startColumnIndex": col0,
                        "endColumnIndex": col0 + 1,
                    },
                    "cell": {
                        "userEnteredFormat": cell_format,
                    },
                    "fields": "userEnteredFormat({})".format(
                        ",".join(field_names)
                    ),
                }
            })

        return requests

    # ------------------------------------------------------------------ #
    # Обновление worksheet после изменений
    # ------------------------------------------------------------------ #

    def _refresh_worksheet(self):
        """
        Перечитывает worksheet, чтобы row_count / col_count были актуальными.
        """
        try:
            self.worksheet = self._g(
                self.spreadsheet.worksheet,
                self.sheet_name,
            )
        except Exception as e:
            p_log("⚠️ Не удалось обновить worksheet: {}".format(e))

    # ------------------------------------------------------------------ #
    # Размер листа
    # ------------------------------------------------------------------ #

    def _ensure_sheet_size(self, total_rows, total_cols):
        """
        Увеличивает лист, если не хватает строк или столбцов.
        """
        try:
            current_rows = int(self.worksheet.row_count)
        except Exception:
            current_rows = 0

        try:
            current_cols = int(self.worksheet.col_count)
        except Exception:
            current_cols = 0

        need_rows = max(current_rows, int(total_rows), 1)
        need_cols = max(current_cols, int(total_cols), 1)

        if need_rows == current_rows and need_cols == current_cols:
            return

        request = {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": self.worksheet.id,
                    "gridProperties": {
                        "rowCount": need_rows,
                        "columnCount": need_cols,
                    },
                },
                "fields": "gridProperties.rowCount,gridProperties.columnCount",
            }
        }

        self._g(
            self.spreadsheet.batch_update,
            {"requests": [request]},
        )

        self._refresh_worksheet()

        p_log(
            "📐 Размер вкладки '{}' изменён: {} строк, {} столбцов".format(
                self.sheet_name,
                need_rows,
                need_cols,
            )
        )

    # ------------------------------------------------------------------ #
    # Замороженные строки и столбцы
    # ------------------------------------------------------------------ #

    def _get_frozen_row_count(self):
        """
        Возвращает количество закреплённых строк на текущей вкладке.
        """
        try:
            frozen = getattr(self.worksheet, "frozen_row_count", None)
            if frozen is not None:
                return int(frozen)
        except Exception:
            pass

        try:
            metadata = self._g(self.spreadsheet.fetch_sheet_metadata)

            for sheet in metadata.get("sheets", []):
                props = sheet.get("properties", {})

                if props.get("sheetId") != self.worksheet.id:
                    continue

                grid = props.get("gridProperties", {})
                return int(grid.get("frozenRowCount", 0))

        except Exception as e:
            p_log("⚠️ Не удалось получить количество замороженных строк: {}".format(e))

        return 0

    def _get_frozen_column_count(self):
        """
        Возвращает количество закреплённых столбцов на текущей вкладке.
        """
        try:
            frozen = getattr(self.worksheet, "frozen_col_count", None)
            if frozen is not None:
                return int(frozen)
        except Exception:
            pass

        try:
            metadata = self._g(self.spreadsheet.fetch_sheet_metadata)

            for sheet in metadata.get("sheets", []):
                props = sheet.get("properties", {})

                if props.get("sheetId") != self.worksheet.id:
                    continue

                grid = props.get("gridProperties", {})
                return int(grid.get("frozenColumnCount", 0))

        except Exception as e:
            p_log("⚠️ Не удалось получить количество замороженных столбцов: {}".format(e))

        return 0

    # ------------------------------------------------------------------ #
    # Очистка значений ячеек без удаления строк
    # ------------------------------------------------------------------ #

    def _clear_row_values(self, row_1based, cols=None):
        """
        Очищает значения одной строки.
        """
        try:
            row_1based = max(1, int(row_1based))
        except (TypeError, ValueError):
            row_1based = 1

        if cols is None:
            try:
                cols = int(self.worksheet.col_count)
            except Exception:
                cols = 1
        else:
            try:
                cols = int(cols)
            except (TypeError, ValueError):
                cols = 1

        cols = max(cols, 1)

        request = {
            "updateCells": {
                "start": {
                    "sheetId": self.worksheet.id,
                    "rowIndex": row_1based - 1,
                    "columnIndex": 0,
                },
                "rows": [{
                    "values": [{} for _ in range(cols)]
                }],
                "fields": "userEnteredValue",
            }
        }

        self._g(
            self.spreadsheet.batch_update,
            {"requests": [request]},
        )

    def _clear_rows_values(self, start_row, end_row, cols=None):
        """
        Очищает значения диапазона строк, не удаляя сами строки.
        """
        try:
            start_row = max(1, int(start_row))
            end_row = max(start_row, int(end_row))
        except (TypeError, ValueError):
            return

        count = end_row - start_row + 1

        if count <= 0:
            return

        if cols is None:
            try:
                cols = int(self.worksheet.col_count)
            except Exception:
                cols = 1
        else:
            try:
                cols = int(cols)
            except (TypeError, ValueError):
                cols = 1

        cols = max(cols, 1)

        empty_rows = []

        for _ in range(count):
            empty_rows.append({
                "values": [{} for _ in range(cols)]
            })

        request = {
            "updateCells": {
                "start": {
                    "sheetId": self.worksheet.id,
                    "rowIndex": start_row - 1,
                    "columnIndex": 0,
                },
                "rows": empty_rows,
                "fields": "userEnteredValue",
            }
        }

        self._g(
            self.spreadsheet.batch_update,
            {"requests": [request]},
        )

    # ------------------------------------------------------------------ #
    # Очистка данных без удаления заголовка
    # ------------------------------------------------------------------ #

    def clear_data_rows(self, start_row=2):
        """
        Удаляет строки данных, начиная с start_row.

        Если первые строки закреплены, код не пытается удалить все
        незакреплённые строки, потому что Google Sheets API запрещает это.
        Вместо этого удаляется максимально возможный диапазон, а одна
        оставшаяся незакреплённая строка очищается.
        """
        try:
            start_row = max(1, int(start_row))
        except (TypeError, ValueError):
            start_row = 2

        try:
            total_rows = int(self.worksheet.row_count)
        except Exception:
            total_rows = 0

        if total_rows < start_row:
            return False

        if start_row <= 1:
            self._g(self.worksheet.clear)
            self._refresh_worksheet()
            p_log("🧹 Лист '{}' очищен полностью".format(self.sheet_name))
            return True

        frozen = self._get_frozen_row_count()

        # Минимально допустимое количество строк после удаления:
        # должна остаться минимум одна незакреплённая строка.
        if frozen > 0:
            min_allowed_rows = frozen + 1
        else:
            min_allowed_rows = 1

        # Если start_row находится внутри замороженной зоны или слишком высоко,
        # удалять строки нельзя. Тогда просто очищаем значения.
        if start_row < min_allowed_rows:
            self._clear_rows_values(start_row, total_rows)
            p_log(
                "🧹 Значения строк {}-{} очищены без удаления "
                "(вкладка '{}', заморожено строк: {})".format(
                    start_row,
                    total_rows,
                    self.sheet_name,
                    frozen,
                )
            )
            return True

        # Если после удаления всех строк с start_row до total_rows
        # остаётся достаточно строк — удаляем весь диапазон.
        if start_row - 1 >= min_allowed_rows:
            self._g(
                self.worksheet.delete_rows,
                start_row,
                total_rows,
            )
            self._refresh_worksheet()

            p_log(
                "🧹 Удалены строки данных с {} до {} во вкладке '{}'".format(
                    start_row,
                    total_rows,
                    self.sheet_name,
                )
            )
            return True

        # Сюда попадаем, если удаление всех строк оставило бы только
        # замороженные строки. Тогда удаляем не все строки, оставляем одну
        # и очищаем её значения.
        if total_rows > start_row:
            self._g(
                self.worksheet.delete_rows,
                start_row,
                total_rows - 1,
            )
            self._refresh_worksheet()

        self._clear_row_values(start_row)

        p_log(
            "🧹 Очищены строки данных во вкладке '{}' "
            "(удаление ограничено замороженными строками)".format(
                self.sheet_name
            )
        )

        return True

    # ------------------------------------------------------------------ #
    # Удаление пустых столбцов
    # ------------------------------------------------------------------ #

    def _get_last_used_column_from_values(self, values):
        """
        Возвращает номер последнего непустого столбца по списку значений.
        Нумерация 1-based.
        """
        last_used = 0

        for row in values or []:
            if not row:
                continue

            for col_idx in range(len(row) - 1, -1, -1):
                value = row[col_idx]

                if value is None:
                    continue

                if str(value).strip() != "":
                    if col_idx + 1 > last_used:
                        last_used = col_idx + 1
                    break

        return last_used

    def delete_empty_columns(self, keep_cols=None, include_middle=False):
        """
        Удаляет пустые столбцы.

        По умолчанию удаляются только пустые столбцы справа, после последнего
        заполненного столбца.

        keep_cols:
            сколько столбцов гарантированно сохранить, даже если они пустые.
            Обычно это ширина ваших данных / sort_col / marker_col.

        include_middle:
            False — удалять только пустые столбцы справа;
            True  — удалять все пустые столбцы, в том числе между данными.

        Возвращает True, если были удалены столбцы.
        """
        try:
            current_cols = int(self.worksheet.col_count)
        except Exception:
            current_cols = 0

        if current_cols <= 1:
            return False

        frozen_cols = self._get_frozen_column_count()

        # Нельзя удалить все незакреплённые столбцы.
        if frozen_cols > 0:
            min_keep = frozen_cols + 1
        else:
            min_keep = 1

        try:
            values = self._g(self.worksheet.get_all_values)
        except Exception as e:
            p_log("⚠️ Не удалось прочитать значения для удаления пустых столбцов: {}".format(e))
            return False

        last_used = self._get_last_used_column_from_values(values)

        if keep_cols is not None:
            try:
                keep_cols = max(0, int(keep_cols))
            except (TypeError, ValueError):
                keep_cols = 0
        else:
            keep_cols = 0

        # ------------------------------------------------------------ #
        # Режим: удалить вообще все пустые столбцы
        # ------------------------------------------------------------ #
        if include_middle:
            empty_cols = []

            for col_1based in range(1, current_cols + 1):
                # Закреплённые столбцы не трогаем.
                if col_1based <= frozen_cols:
                    continue

                # Если сказано сохранить первые keep_cols столбцов — не трогаем.
                if keep_cols and col_1based <= keep_cols:
                    continue

                is_empty = True

                for row in values:
                    idx = col_1based - 1

                    if idx < len(row):
                        value = row[idx]
                        if value is not None and str(value).strip() != "":
                            is_empty = False
                            break

                if is_empty:
                    empty_cols.append(col_1based)

            if not empty_cols:
                return False

            requests = []
            deleted_count = 0

            # Удаляем справа налево, чтобы индексы не съезжали.
            for col_1based in sorted(empty_cols, reverse=True):
                # После удаления должно остаться минимум min_keep столбцов.
                if current_cols - deleted_count - 1 < min_keep:
                    break

                requests.append({
                    "deleteDimension": {
                        "range": {
                            "sheetId": self.worksheet.id,
                            "dimension": "COLUMNS",
                            "startIndex": col_1based - 1,
                            "endIndex": col_1based,
                        }
                    }
                })

                deleted_count += 1

            if not requests:
                return False

            self._g(
                self.spreadsheet.batch_update,
                {"requests": requests},
            )

            self._refresh_worksheet()

            p_log(
                "🧹 Удалено {} пустых столбцов во вкладке '{}'".format(
                    deleted_count,
                    self.sheet_name,
                )
            )

            return True

        # ------------------------------------------------------------ #
        # Режим по умолчанию: удалить только пустые столбцы справа
        # ------------------------------------------------------------ #
        final_cols = max(
            1,
            min_keep,
            last_used,
            keep_cols,
        )

        if current_cols <= final_cols:
            return False

        request = {
            "deleteDimension": {
                "range": {
                    "sheetId": self.worksheet.id,
                    "dimension": "COLUMNS",
                    "startIndex": final_cols,
                    "endIndex": current_cols,
                }
            }
        }

        self._g(
            self.spreadsheet.batch_update,
            {"requests": [request]},
        )

        self._refresh_worksheet()

        deleted_count = current_cols - final_cols

        p_log(
            "🧹 Удалено {} пустых столбцов справа во вкладке '{}'".format(
                deleted_count,
                self.sheet_name,
            )
        )

        return True

    # ------------------------------------------------------------------ #
    # Условное форматирование
    # ------------------------------------------------------------------ #

    def remove_all_conditional_formats(self):
        """
        Удаляет все правила условного форматирования на текущей вкладке.
        """
        try:
            metadata = self._g(self.spreadsheet.fetch_sheet_metadata)
        except Exception as e:
            p_log("⚠️ Не удалось получить metadata для удаления условного форматирования: {}".format(e))
            return False

        requests = []

        for sheet in metadata.get("sheets", []):
            props = sheet.get("properties", {})

            if props.get("sheetId") != self.worksheet.id:
                continue

            rules = sheet.get("conditionalFormats", [])

            for idx in range(len(rules) - 1, -1, -1):
                requests.append({
                    "deleteConditionalFormatRule": {
                        "sheetId": self.worksheet.id,
                        "index": idx,
                    }
                })

            break

        if requests:
            self._g(
                self.spreadsheet.batch_update,
                {"requests": requests},
            )

            p_log(
                "🧹 Удалено {} правил условного форматирования во вкладке '{}'".format(
                    len(requests),
                    self.sheet_name,
                )
            )

        return True

    def apply_gradient_to_columns(
        self,
        columns,
        mode=GRADIENT_MODE_RED_TO_GREEN,
        start_row=2,
    ):
        """
        Создаёт градиентное условное форматирование для указанных столбцов.

        columns:
            столбцы в любом удобном виде:
                "C"
                ["C", "D"]
                "C, D"
                2, 3   # 0-based: 2=C, 3=D

        mode:
            "red_to_green" — минимальные значения красные, максимальные зелёные.
            "green_to_red" — минимальные значения зелёные, максимальные красные.

        start_row:
            1-based номер первой строки данных.
            Если шапка в строке 1, обычно передают 2.
        """
        cols0 = self._columns_to_0based_list(columns)

        if not cols0:
            p_log("⚠️ Нет корректных столбцов для градиентного форматирования")
            return False

        try:
            start_row = max(1, int(start_row))
        except (TypeError, ValueError):
            start_row = 2

        mode = str(mode or "").strip().lower()

        if mode in ("green_to_red", "greenred", "green-to-red", "g_to_r", "g2r"):
            min_color = dict(GRADIENT_GREEN)
            max_color = dict(GRADIENT_RED)
            mode_name = "green_to_red"
        else:
            min_color = dict(GRADIENT_RED)
            max_color = dict(GRADIENT_GREEN)
            mode_name = "red_to_green"

        requests = []

        for index, col0 in enumerate(cols0):
            rng = {
                "sheetId": self.worksheet.id,
                "startRowIndex": start_row - 1,
                "startColumnIndex": col0,
                "endColumnIndex": col0 + 1,
                # endRowIndex не указываем, чтобы правило работало
                # и на новых строках.
            }

            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [rng],
                        "gradientRule": {
                            "minpoint": {
                                "type": "MIN",
                                "color": min_color,
                            },
                            "maxpoint": {
                                "type": "MAX",
                                "color": max_color,
                            },
                        },
                    },
                    "index": index,
                }
            })

        if not requests:
            return False

        self._g(
            self.spreadsheet.batch_update,
            {"requests": requests},
        )

        p_log(
            "🎨 Градиент '{}' применён к {} столбцам во вкладке '{}'".format(
                mode_name,
                len(cols0),
                self.sheet_name,
            )
        )

        return True

    # ------------------------------------------------------------------ #
    # Базовое форматирование строк данных
    # ------------------------------------------------------------------ #

    def _data_format_requests(self, start_row, rows_count, total_cols):
        """
        Базовое форматирование строк данных:
        - убрать жирный шрифт.

        Выравнивание теперь задаётся отдельно через alignments.
        """
        try:
            rows_count = int(rows_count)
            total_cols = int(total_cols)
            start_row = int(start_row)
        except (TypeError, ValueError):
            return []

        if rows_count <= 0 or total_cols <= 0:
            return []

        start_index = start_row - 1
        end_index = start_index + rows_count

        requests = []

        # Убираем жирный шрифт для всех ячеек данных.
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": self.worksheet.id,
                    "startRowIndex": start_index,
                    "endRowIndex": end_index,
                    "startColumnIndex": 0,
                    "endColumnIndex": total_cols,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "bold": False,
                        }
                    }
                },
                "fields": "userEnteredFormat.textFormat.bold",
            }
        })

        return requests

    # ------------------------------------------------------------------ #
    # Запись данных без заголовка
    # ------------------------------------------------------------------ #

    def fill_rows(
        self,
        rows,
        start_row=2,
        total_cols=None,
        clear_sheet=False,
        clear_data=False,
        first_row=None,
        trim_empty_columns=True,
        clear_conditional_formats=True,
        red_to_green_columns=None,
        green_to_red_columns=None,
        alignments=None,
    ):
        """
        Записывает строки данных без заголовка.

        rows:
            список строк данных

        start_row:
            1-based номер строки, с которой нужно начать запись данных.
            Если шапка в строке 1 — используйте 2.
            Если шапки нет — используйте 1.

        total_cols:
            количество столбцов. Если не указано, берётся по максимальной
            длине строк / first_row / columns for gradient / alignments.

        clear_sheet:
            True — очистить ВЕСЬ лист.
            Внимание: это удалит и ваш заголовок / первую строку.

        clear_data:
            True — удалить только строки данных начиная с start_row.

        first_row:
            список значений для первой строки.
            Если передан список/кортеж — первая строка заменяется.
            Если передано что-то другое или None — ничего не делаем.

        trim_empty_columns:
            True — после записи удалить пустые столбцы справа.

        clear_conditional_formats:
            True — удалить все правила условного форматирования перед
            созданием новых правил.

        red_to_green_columns:
            столбцы для градиента "красный -> зелёный".

        green_to_red_columns:
            столбцы для градиента "зелёный -> красный".

        alignments:
            словарь выравниваний для строк данных.
            Пример:
                {
                    "A": "middle",
                    "B": "left",
                    "C": "right",
                }
            По умолчанию None — выравнивание не применяется.
        """
        rows = self._prepare_rows(rows)
        first_row = self._prepare_first_row(first_row)

        # Если передана первая строка, данные должны начинаться минимум со 2-й строки.
        if first_row is not None:
            try:
                start_row = max(2, int(start_row))
            except (TypeError, ValueError):
                start_row = 2
        else:
            try:
                start_row = max(1, int(start_row))
            except (TypeError, ValueError):
                start_row = 2

        if not rows and first_row is None:
            p_log("⚠️ Нет строк и нет first_row для записи")
            return True

        alignment_columns = []
        if isinstance(alignments, dict):
            alignment_columns = list(alignments.keys())

        extra_columns = self._flatten_columns(
            red_to_green_columns,
            green_to_red_columns,
            alignment_columns,
        )

        total_cols = self._resolve_total_cols(
            rows=rows,
            total_cols=total_cols,
            first_row=first_row,
            extra_columns=extra_columns,
        )

        if total_cols <= 0:
            total_cols = 1

        if clear_sheet:
            self._g(self.worksheet.clear)
        elif clear_data:
            self.clear_data_rows(start_row)

        needed_rows = start_row - 1 + len(rows)

        if first_row is not None:
            needed_rows = max(needed_rows, 1)

        self._ensure_sheet_size(
            total_rows=needed_rows,
            total_cols=total_cols,
        )

        requests = []

        # -------------------------------------------------- #
        # Запись первой строки, если передали список
        # -------------------------------------------------- #
        if first_row is not None:
            try:
                current_cols = int(self.worksheet.col_count)
            except Exception:
                current_cols = total_cols

            # Чтобы реально заменить первую строку, очищаем её как минимум
            # на ширину текущих данных / первой строки / текущего листа.
            first_row_cols = max(
                total_cols,
                len(first_row),
                current_cols,
                1,
            )

            first_row_values = list(first_row)

            if len(first_row_values) < first_row_cols:
                first_row_values.extend([""] * (first_row_cols - len(first_row_values)))
            elif len(first_row_values) > first_row_cols:
                first_row_values = first_row_values[:first_row_cols]

            requests.append({
                "updateCells": {
                    "start": {
                        "sheetId": self.worksheet.id,
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "rows": [{
                        "values": [self._build_cell(value) for value in first_row_values]
                    }],
                    "fields": "userEnteredValue",
                }
            })

        # -------------------------------------------------- #
        # Запись основных данных
        # -------------------------------------------------- #
        if rows:
            api_rows = []

            for row in rows:
                row = list(row)

                if len(row) < total_cols:
                    row.extend([""] * (total_cols - len(row)))
                elif len(row) > total_cols:
                    row = row[:total_cols]

                api_rows.append({
                    "values": [self._build_cell(value) for value in row]
                })

            requests.append({
                "updateCells": {
                    "start": {
                        "sheetId": self.worksheet.id,
                        "rowIndex": start_row - 1,
                        "columnIndex": 0,
                    },
                    "rows": api_rows,
                    "fields": "userEnteredValue",
                }
            })

            # Базовое форматирование: убрать жирный.
            requests.extend(
                self._data_format_requests(
                    start_row=start_row,
                    rows_count=len(rows),
                    total_cols=total_cols,
                )
            )

            # Выравнивание строк данных, если передано.
            if alignments:
                requests.extend(
                    self._alignment_requests(
                        alignments=alignments,
                        start_row=start_row,
                        rows_count=len(rows),
                    )
                )

        if requests:
            self._g(
                self.spreadsheet.batch_update,
                {"requests": requests},
            )

        # -------------------------------------------------- #
        # Удаление пустых столбцов справа
        # -------------------------------------------------- #
        if trim_empty_columns:
            self.delete_empty_columns(
                keep_cols=total_cols,
                include_middle=False,
            )

        # -------------------------------------------------- #
        # Условное форматирование
        # -------------------------------------------------- #
        if clear_conditional_formats:
            self.remove_all_conditional_formats()

        if red_to_green_columns:
            self.apply_gradient_to_columns(
                columns=red_to_green_columns,
                mode=GRADIENT_MODE_RED_TO_GREEN,
                start_row=start_row,
            )

        if green_to_red_columns:
            self.apply_gradient_to_columns(
                columns=green_to_red_columns,
                mode=GRADIENT_MODE_GREEN_TO_RED,
                start_row=start_row,
            )

        if first_row is not None:
            p_log("✅ Записана первая строка: {}".format(first_row))

        p_log(
            "✅ Записано {} строк данных начиная со строки {}".format(
                len(rows),
                start_row,
            )
        )

        return True

    # ------------------------------------------------------------------ #
    # Сортировка
    # ------------------------------------------------------------------ #

    def sort_data_range(
        self,
        start_row,
        rows_count,
        sort_col,
        ascending=True,
        total_cols=None,
    ):
        """
        Сортирует диапазон данных через Google Sheets API.

        start_row:
            1-based номер первой строки данных.
            Например, если шапка в строке 1, передавайте 2.

        rows_count:
            сколько строк данных сортировать.

        sort_col:
            столбец сортировки.
            Рекомендуется передавать буквой: "A", "B", "C", "D".
            Если передаётся int, считается 0-based:
                0 -> A
                1 -> B
                2 -> C
                3 -> D

        ascending:
            True  — по возрастанию
            False — по убыванию

        total_cols:
            ширина диапазона сортировки.
            Если не указано, определяется по sort_col.
        """
        try:
            start_row = max(1, int(start_row))
        except (TypeError, ValueError):
            p_log("⚠️ Некорректный start_row")
            return False

        try:
            rows_count = int(rows_count)
        except (TypeError, ValueError):
            p_log("⚠️ Некорректный rows_count")
            return False

        if rows_count <= 1:
            return True

        sort_col_0 = self._column_to_0based(sort_col)

        if sort_col_0 is None or sort_col_0 < 0:
            p_log("⚠️ Некорректный столбец сортировки: {}".format(sort_col))
            return False

        total_cols = self._resolve_total_cols(
            total_cols=total_cols,
            sort_col=sort_col,
        )

        if total_cols <= sort_col_0:
            total_cols = sort_col_0 + 1

        if total_cols <= 0:
            total_cols = 1

        sort_order = "ASCENDING" if ascending else "DESCENDING"

        request = {
            "sortRange": {
                "range": {
                    "sheetId": self.worksheet.id,
                    "startRowIndex": start_row - 1,
                    "endRowIndex": start_row - 1 + rows_count,
                    "startColumnIndex": 0,
                    "endColumnIndex": total_cols,
                },
                "sortSpecs": [
                    {
                        "dimensionIndex": sort_col_0,
                        "sortOrder": sort_order,
                    }
                ],
            }
        }

        self._g(
            self.spreadsheet.batch_update,
            {"requests": [request]},
        )

        p_log(
            "🔃 Сортировка выполнена: строки {}-{}, столбец {}, {}".format(
                start_row,
                start_row + rows_count - 1,
                sort_col,
                sort_order,
            )
        )

        return True

    # ------------------------------------------------------------------ #
    # Чтение данных после сортировки
    # ------------------------------------------------------------------ #

    def _read_data_rows(self, start_row, rows_count, total_cols=None):
        """
        Читает строки данных из таблицы.

        Используется после сортировки, чтобы красить уже реальный
        порядок строк в таблице, а не исходный список в Python.
        """
        try:
            start_row = max(1, int(start_row))
            rows_count = max(0, int(rows_count))
        except (TypeError, ValueError):
            return []

        if rows_count <= 0:
            return []

        all_values = self._g(self.worksheet.get_all_values)

        start_idx = start_row - 1
        end_idx = start_idx + rows_count

        raw_rows = []

        if start_idx < len(all_values):
            raw_rows = all_values[start_idx:end_idx]

        result = []

        for row in raw_rows:
            row = list(row)

            if total_cols is not None:
                if len(row) < total_cols:
                    row.extend([""] * (total_cols - len(row)))
                elif len(row) > total_cols:
                    row = row[:total_cols]

            result.append(row)

        # Если таблица вернула меньше строк, дополняем пустыми.
        while len(result) < rows_count:
            result.append([])

        return result

    # ------------------------------------------------------------------ #
    # Поиск маркера в строке
    # ------------------------------------------------------------------ #

    def _row_contains_marker(
        self,
        row,
        marker_text,
        marker_col_0,
        exact,
        case_sensitive,
    ):
        """
        Возвращает True, если маркер найден в строке.

        marker_col_0:
            None — искать во всех ячейках строки.
            0, 1, 2, 3... — искать только в конкретной колонке.
        """
        if marker_col_0 is None:
            values = row
        else:
            if marker_col_0 < 0 or marker_col_0 >= len(row):
                return False

            values = [row[marker_col_0]]

        for value in values:
            if value is None:
                text = ""
            else:
                text = str(value)

            if not case_sensitive:
                text = text.lower()

            if exact:
                if text == marker_text:
                    return True
            else:
                if marker_text in text:
                    return True

        return False

    # ------------------------------------------------------------------ #
    # Покраска строк
    # ------------------------------------------------------------------ #

    def paint_rows_by_marker(
        self,
        rows,
        marker="[SLAVS]",
        marker_col=None,
        color=None,
        exact=False,
        case_sensitive=True,
        start_row=2,
        total_cols=None,
        reset_background=True,
    ):
        """
        Красит строки, где встречается маркер.

        Это статическая покраска, не условное форматирование.

        rows:
            список строк в том порядке, в котором они находятся в таблице.

        marker:
            строка для поиска, например "[SLAVS]".

        marker_col:
            столбец для поиска.
            Рекомендуется передавать буквой: "A", "B", "C", "D".
            Если передаётся int, считается 0-based:
                0 -> A
                1 -> B
                2 -> C
                3 -> D

        color:
            цвет фона в формате Google Sheets API:
            {
                "red": 1.0,
                "green": 0.8,
                "blue": 0.8,
            }

        exact:
            False — подходит "[SLAVS] bonus"
            True  — подходит только точное совпадение "[SLAVS]"

        case_sensitive:
            True  — учитывать регистр
            False — не учитывать

        start_row:
            1-based номер первой строки данных.

        total_cols:
            количество столбцов для покраски.

        reset_background:
            True — сначала сбросить фон строк данных в белый,
                   затем покрасить совпавшие строки.
        """
        rows = self._prepare_rows(rows)

        if not rows:
            return True

        if marker is None or str(marker) == "":
            p_log("⚠️ marker пуст — покраска пропущена")
            return True

        try:
            start_row = max(1, int(start_row))
        except (TypeError, ValueError):
            start_row = 2

        total_cols = self._resolve_total_cols(
            rows=rows,
            total_cols=total_cols,
            marker_col=marker_col,
        )

        if total_cols <= 0:
            p_log("⚠️ Не удалось определить количество столбцов для покраски")
            return False

        color = _normalize_color(color)
        white_color = _normalize_color(WHITE_COLOR)

        requests = []

        # Сбрасываем фон для всех строк данных.
        if reset_background:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": self.worksheet.id,
                        "startRowIndex": start_row - 1,
                        "endRowIndex": start_row - 1 + len(rows),
                        "startColumnIndex": 0,
                        "endColumnIndex": total_cols,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": white_color,
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            })

        if case_sensitive:
            prepared_marker = str(marker)
        else:
            prepared_marker = str(marker).lower()

        marker_col_0 = self._column_to_0based(marker_col)

        painted_count = 0

        for row_index, row in enumerate(rows):
            hit = self._row_contains_marker(
                row=row,
                marker_text=prepared_marker,
                marker_col_0=marker_col_0,
                exact=exact,
                case_sensitive=case_sensitive,
            )

            if not hit:
                continue

            api_row_index = start_row - 1 + row_index

            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": self.worksheet.id,
                        "startRowIndex": api_row_index,
                        "endRowIndex": api_row_index + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": total_cols,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color,
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            })

            painted_count += 1

        if requests:
            self._g(
                self.spreadsheet.batch_update,
                {"requests": requests},
            )

        p_log(
            "🎨 Покрашено строк: {} (маркер: {})".format(
                painted_count,
                marker,
            )
        )

        return True

    # ------------------------------------------------------------------ #
    # Удобный метод: заполнить, отсортировать и покрасить
    # ------------------------------------------------------------------ #

    def fill_and_paint(
        self,
        rows,
        start_row=2,
        marker="[SLAVS]",
        marker_col=None,
        color=None,
        exact=False,
        case_sensitive=True,
        total_cols=None,
        sort_col=None,
        ascending=True,
        clear_sheet=False,
        clear_data=False,
        reset_background=True,
        first_row=None,
        trim_empty_columns=True,
        clear_conditional_formats=True,
        red_to_green_columns=None,
        green_to_red_columns=None,
        alignments=None,
    ):
        """
        Заполняет данные, при необходимости сортирует и красит строки.

        start_row:
            с какой строки писать данные.
            Если шапка в строке 1 — передавайте 2.

        sort_col:
            столбец сортировки.
            Рекомендуется передавать буквой: "A", "B", "C", "D".

        ascending:
            True  — по возрастанию
            False — по убыванию

        clear_sheet:
            True — очистить весь лист, включая ваш заголовок.

        clear_data:
            True — удалить старые строки данных начиная с start_row.
            Заголовок выше start_row останется.

        first_row:
            список значений для первой строки.
            Если передаётся список/кортеж — первая строка заменяется.
            Если передаётся не список или None — первая строка не трогаем.

        trim_empty_columns:
            True — после записи удалить пустые столбцы справа.

        clear_conditional_formats:
            True — удалить все правила условного форматирования перед
            созданием новых правил.

        red_to_green_columns:
            столбцы для градиента "красный -> зелёный".
            Пример: ["C", "D"]

        green_to_red_columns:
            столбцы для градиента "зелёный -> красный".
            Пример: ["E", "F"]

        alignments:
            словарь выравниваний для строк данных.
            Пример:
                {
                    "A": "middle",
                    "B": "left",
                    "C": "right",
                }
        """
        rows = self._prepare_rows(rows)
        first_row = self._prepare_first_row(first_row)

        # Если мы заменяем первую строку, данные не должны начинаться с 1-й строки.
        if first_row is not None:
            try:
                start_row = max(2, int(start_row))
            except (TypeError, ValueError):
                start_row = 2

        alignment_columns = []
        if isinstance(alignments, dict):
            alignment_columns = list(alignments.keys())

        extra_columns = self._flatten_columns(
            red_to_green_columns,
            green_to_red_columns,
            alignment_columns,
        )

        total_cols = self._resolve_total_cols(
            rows=rows,
            total_cols=total_cols,
            sort_col=sort_col,
            marker_col=marker_col,
            first_row=first_row,
            extra_columns=extra_columns,
        )

        ok = self.fill_rows(
            rows=rows,
            start_row=start_row,
            total_cols=total_cols,
            clear_sheet=clear_sheet,
            clear_data=clear_data,
            first_row=first_row,
            trim_empty_columns=trim_empty_columns,
            clear_conditional_formats=clear_conditional_formats,
            red_to_green_columns=red_to_green_columns,
            green_to_red_columns=green_to_red_columns,
            alignments=alignments,
        )

        if not ok:
            return False

        rows_for_paint = rows

        # Если нужна сортировка — сначала сортируем диапазон в таблице,
        # затем перечитываем данные, чтобы красить уже новые строки.
        if sort_col is not None and len(rows) > 1:
            sorted_ok = self.sort_data_range(
                start_row=start_row,
                rows_count=len(rows),
                sort_col=sort_col,
                ascending=ascending,
                total_cols=total_cols,
            )

            if sorted_ok:
                rows_for_paint = self._read_data_rows(
                    start_row=start_row,
                    rows_count=len(rows),
                    total_cols=total_cols,
                )

        if marker is not None and str(marker) != "":
            return self.paint_rows_by_marker(
                rows=rows_for_paint,
                marker=marker,
                marker_col=marker_col,
                color=color,
                exact=exact,
                case_sensitive=case_sensitive,
                start_row=start_row,
                total_cols=total_cols,
                reset_background=reset_background,
            )

        return True