from module.all_function import save_file
from module.operation import get_statistic_clan
from setting import *
from module.toplist import get_statistic, dict_values_difference, write_2dlist_to_excel

if __name__ == "__main__":
    if program_selection:
        all_dct = get_statistic_clan()
        if write_flag:
            print(f"Записать новые данные в {FILE_NAME}? [y/n]")
            save_file(all_dct, FILE_NAME)
    else:
        stat_dct = get_statistic()  # получить данные статистики 0-2000
        difference_list, difference_loss = dict_values_difference(stat_dct)  # сравнить полученные данные с сохраненными
        write_2dlist_to_excel(difference_list)  # сохранить результат в exel-файл
        if write_flag:
            print(f"Записать новые данные в {STAT_FILE_NAME}? [y/n]")
            save_file(stat_dct, STAT_FILE_NAME)
            print(f"Записать новые данные в {STAT_FILE_LOSS}? [y/n]")
            save_file(difference_loss, STAT_FILE_LOSS)
