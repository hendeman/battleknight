import os
from typing import Union, Optional

from openpyxl.utils import get_column_letter
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment

from logs.logs import p_log
from module.all_function import get_prefix_url, day, syntax_day
from module.operation import DATA_CHANGE_FILE
from setting import today, STAT_FILE_NAME

from datetime import datetime
import pandas as pd


def aggregate_castle_stats(diff_list, raw_headers):
    """Группирует данные по Орденам и рассчитывает процентные показатели."""
    df = pd.DataFrame(diff_list, columns=raw_headers)
    df['Орден'] = df['Орден'].replace('', 'no orden')

    # Агрегация
    grouped_df = df.groupby('Орден').agg({'Добыча': 'sum', 'Потери': 'sum'}).reset_index()

    # Расчет метрик
    total_dobych = grouped_df['Добыча'].sum()
    grouped_df['доб(%)'] = ((grouped_df['Добыча'] / total_dobych) * 100).round(2) if total_dobych else 0
    grouped_df['пот/доб (%)'] = (grouped_df['Потери'] / grouped_df['Добыча'] * 100).round(2)

    return grouped_df.values.tolist()


def get_excel_path(write_flag: bool) -> str:
    """Возвращает путь к итоговому Excel-файлу."""
    pref = "_all" if write_flag else ""
    pref_lang = get_prefix_url()
    filename = f"stat_{today.day:02d}_{today.month:02d}_{today.year}{pref}_{pref_lang}.xlsx"
    return os.path.join("bk", "result_xlsx", filename)


def get_period_info(base_stat_file: Optional[Union[str, bytes]] = None) -> list:
    """Формирует текстовое описание периода для нового отчета статистики.

    Функция берет сохраненный файл предыдущей статистики, рассчитывает
    на его основе количество прошедших дней (сколько времени прошло с момента
    последнего сохранения) и возвращает временные границы для нового отчета.

    Args:
        base_stat_file: Путь к сохраненному файлу прошлой статистики,
             который выступает точкой отсчета для нового периода.

    Returns:
        Список из трех строк:
            1. Заголовок с числом прошедших дней и правильным склонением слова.
            2. Дата и время начала нового периода (модификация DATA_CHANGE_FILE).
            3. Дата и время окончания периода (текущий момент).
    """
    if base_stat_file is None:
        base_stat_file = STAT_FILE_NAME

    days_have_passed = day(base_stat_file)

    try:
        # Получаем время модификации файла в секундах (timestamp)
        modification_time = os.path.getmtime(base_stat_file)
        # Конвертируем секунды в объект datetime
        file_datetime = datetime.fromtimestamp(modification_time)
        date_from = file_datetime.strftime("%d.%m.%Y %H:%M")
    except (FileNotFoundError, OSError):
        # Защита на случай, если файла еще нет (например, первый запуск)
        date_from = "неизвестно (файл не найден)"

    date_to = datetime.now().strftime("%d.%m.%Y %H:%M")

    return [
        f"Статистика за {days_have_passed} {syntax_day(days_have_passed)}:",
        f"с {date_from}",
        f"по {date_to}",
    ]


def set_column_widths(sheet):
    for col in sheet.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        sheet.column_dimensions[col_letter].width = max(max_len + 3, 10)


def add_data_to_sheet(sheet, period, header, data):
    sheet.append(period)
    sheet.append(header)
    for cell in sheet[2]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='right')
    for row in data:
        sheet.append(row)
    set_column_widths(sheet)


def write_2dlist_to_excel(sheet_name: str, header: list, data: list,
                          write_flag: bool, period: list | None = None):
    """
    Добавляет ОДИН лист в Excel-книгу и сохраняет её.
    Если файл уже существует — открывает его, иначе создаёт новую книгу.

    :param sheet_name: имя листа
    :param header:     заголовки колонок
    :param data:       2D-список с данными
    :param write_flag: влияет на имя файла (суффикс `_all`)
    :param period:     шапка-период; если None — формируется автоматически
    """
    excel_file_path = get_excel_path(write_flag)
    period = period or get_period_info()

    os.makedirs(os.path.dirname(excel_file_path), exist_ok=True)

    if os.path.exists(excel_file_path):
        workbook = load_workbook(excel_file_path)
    else:
        workbook = Workbook()
        # удаляем дефолтный пустой лист при первом создании
        workbook.remove(workbook.active)

    if sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
    else:
        sheet = workbook.create_sheet(title=sheet_name)

    add_data_to_sheet(sheet, period, header, data)
    workbook.save(excel_file_path)

    p_log(f"Лист '{sheet_name}' сохранён в файл {excel_file_path}")
