import os

from logs.logs import p_log, setup_logging
from module.all_function import save_file, save_json_file, load_json_file
from module.cli import arg_parser
from module.operation import get_statistic_clan, get_statistic, dict_values_difference
from setting import FILE_NAME, STAT_FILE_NAME, STAT_FILE_LOSS, today
from sheet.custom_sheet import CustomStatsSheet
from sheet.exel_sheet import write_2dlist_to_excel, aggregate_castle_stats, get_period_info
from sheet.fill_sheet import CREDENTIALS_FILE, SHEET_URL

SHEET_HEADER_GAMERS = ['Имя', 'Орден', 'Уровень', 'Добыча', 'Потери', 'пот/доб (%)', 'Бои', 'Победы', 'Поражения']
SHEET_HEADER_CASTLES = ['Орден', 'Добыча', 'Потери', 'доб(%)', 'пот/доб (%)']
SHEET_NAME_GAMERS = "статистика"
SHEET_NAME_CASTLES = "ордены"

PLAYER_STATISTICS = f"player_{today.day:02d}_{today.month:02d}_{today.year}.json"
ALL_STATISTICS = f"all_{today.day:02d}_{today.month:02d}_{today.year}.json"
LOSS_STATISTICS = f"loss_{today.day:02d}_{today.month:02d}_{today.year}.json"

SAVE_DIR = "save"  # путь, куда сохраняются json-файлы (используется в save_json_file)


def export_to_google_sheet(data_list, **kwargs):
    sheet_name = kwargs.get('sheet_name', 'test')
    start_row = kwargs.get('start_row', 3)
    first_row = kwargs.get('first_row', ["Статистика:", "", ""])
    color = kwargs.get('color', {"red": 1.0, "green": 0.8, "blue": 0.8})

    sheet = CustomStatsSheet(
        credentials_file=CREDENTIALS_FILE,
        sheet_url_or_id=SHEET_URL,
        sheet_name=sheet_name,  # имя новой вкладки
        auto_format=False,  # важно: не применять стандартную шапку модуля
    )
    sheet.fill_and_paint(
        rows=data_list,
        start_row=start_row,
        first_row=first_row,
        marker="",
        marker_col='B',
        color=color,
        sort_col="D",
        ascending=False,
        clear_data=True,
        red_to_green_columns=None,
        green_to_red_columns=None,
        alignments={
            "A": {"horizontal": "left"},
            "B": {"horizontal": "middle"},
            "C": {"horizontal": "middle"},
        }
    )


def _today_files_exist() -> bool:
    """Проверяет, что все три json-файла с сегодняшней датой уже сохранены."""
    return all(
        os.path.isfile(os.path.join(SAVE_DIR, name))
        for name in (PLAYER_STATISTICS, LOSS_STATISTICS, ALL_STATISTICS)
    )


if __name__ == "__main__":
    setup_logging()
    parser = arg_parser()

    args = parser.parse_args()

    program_selection = args.program_selection
    write_flag = args.write_flag

    if not program_selection:
        all_dct = get_statistic_clan(write_flag=write_flag)
        if write_flag:
            p_log(f"Записать новые данные в {FILE_NAME}? [y/n]")
            save_file(all_dct, FILE_NAME)
    else:
        # --- Новая проверка: если файлы за сегодня уже есть — грузим их ---
        if _today_files_exist():
            p_log("Найдены сохранённые данные за сегодня — загружаю из json-файлов.")
            difference_list = load_json_file(SAVE_DIR, PLAYER_STATISTICS)
            difference_loss = load_json_file(SAVE_DIR, LOSS_STATISTICS)
            stat_dct = load_json_file(SAVE_DIR, ALL_STATISTICS)
        else:
            stat_dct = get_statistic()  # получить данные статистики 0-2000
            difference_list, difference_loss = dict_values_difference(stat_dct)  # сравнить с сохранёнными

        try:
            # Сохранить в exel статистику по онлайну
            write_2dlist_to_excel(
                sheet_name=SHEET_NAME_GAMERS,
                header=SHEET_HEADER_GAMERS,
                data=difference_list,
                write_flag=write_flag
            )
            # Сохранить в exel статистику по кланам
            castle_data = aggregate_castle_stats(difference_list, SHEET_HEADER_GAMERS)
            write_2dlist_to_excel(
                sheet_name=SHEET_NAME_CASTLES,
                header=SHEET_HEADER_CASTLES,
                data=castle_data,  # FIX: было difference_list
                write_flag=write_flag
            )
        except Exception as exel_error:
            p_log(f"Ошибка в сохранении exel-таблицы {exel_error}")
            save_json_file(difference_list, SAVE_DIR, PLAYER_STATISTICS)
            save_json_file(difference_loss, SAVE_DIR, LOSS_STATISTICS)
            save_json_file(stat_dct, SAVE_DIR, ALL_STATISTICS)

        # --- Google Sheets: сохраняем json при ошибке ---
        try:
            export_to_google_sheet(
                difference_list,
                first_row=get_period_info(),
            )
        except Exception as sheet_error:
            p_log(f"Ошибка в сохранении google-таблицы {sheet_error}")
            save_json_file(difference_list, SAVE_DIR, PLAYER_STATISTICS)
            save_json_file(difference_loss, SAVE_DIR, LOSS_STATISTICS)
            save_json_file(stat_dct, SAVE_DIR, ALL_STATISTICS)

        if write_flag:
            p_log(f"Записать новые данные в {STAT_FILE_NAME}? [y/n]")
            save_file(stat_dct, STAT_FILE_NAME)
            p_log(f"Записать новые данные в {STAT_FILE_LOSS}? [y/n]")
            save_file(difference_loss, STAT_FILE_LOSS)
