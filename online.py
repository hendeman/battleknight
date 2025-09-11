from logs.logs import p_log, setup_logging
from module.all_function import save_file
from module.cli import arg_parser
from module.operation import get_statistic_clan, get_statistic, dict_values_difference, write_2dlist_to_excel
from setting import FILE_NAME, STAT_FILE_NAME, STAT_FILE_LOSS

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
        stat_dct = get_statistic()  # получить данные статистики 0-2000
        difference_list, difference_loss = dict_values_difference(stat_dct)  # сравнить полученные данные с сохраненными
        write_2dlist_to_excel(difference_list, write_flag=write_flag)  # сохранить результат в exel-файл
        if write_flag:
            p_log(f"Записать новые данные в {STAT_FILE_NAME}? [y/n]")
            save_file(stat_dct, STAT_FILE_NAME)
            p_log(f"Записать новые данные в {STAT_FILE_LOSS}? [y/n]")
            save_file(difference_loss, STAT_FILE_LOSS)
