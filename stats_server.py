import time
from bs4 import BeautifulSoup

from logs.logs import p_log, setup_logging
from module.all_function import get_html_files, check_file_exists, load_json_file, backup_json_file, save_json_file
from module.data_pars import pars_player
from module.excel_function import write_2dlist_to_excel
from module.http_requests import make_request, post_request
from setting import *


def fetch_data(source_dir, output_filename, network=False):
    if network:
        # Шаг 1: Сбор данных из сети и сохранение в файлы
        make_request(url_stat)
        p_log("Обработка запросов:")

        for i in range(0, 2000, 100):
            param = {
                'highscoreOffset': str(i),
                'sort': 'loot',
                'searchUser': ''
            }
            p_log(f"Будет отправлен запрос в топ-лист {i}:{i + 100}")
            stat = post_request(url_stat, param)
            with open(f'{source_dir}\\{i + 100}_BattleKnight.html', 'w', encoding='utf-8') as file:
                file.write(stat.text)
            time.sleep(2)

    # Общая часть для обоих источников
    combined_data = {}
    list_html_files = get_html_files(source_dir)
    for file_path in list_html_files:
        with open(source_dir + file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        soup = BeautifulSoup(html_content, 'lxml')
        combined_data.update(pars_player(soup))  # Предполагается, что pars_player возвращает dict

    save_json_file(combined_data, path_json, output_filename)


def get_statistic():
    if check_file_exists(path_json, name_file_old):
        p_log(f"Файл {name_file_old} существует!")
    else:
        p_log(f"Файл data.json не найден. Будет сформирован из файлов {statistic_old_dir}")
        if get_html_files(statistic_old_dir):
            fetch_data(source_dir=statistic_old_dir, output_filename=name_file_old)
        else:
            p_log(f"В {statistic_old_dir} файлы не найдены. Будет выполнен первичный сбор статистики.")
            fetch_data(source_dir=statistic_old_dir, output_filename=name_file_old, network=True)
            raise "Для формирования статистики запустите скрипт через несколько дней"
    fetch_data(source_dir=statistic_new_dir, output_filename=name_file_new, network=True)


def union_list(name_file_1: str, name_file_2: str) -> list:
    dct_old = load_json_file(path_json, name_file=name_file_1)
    dct_new = load_json_file(path_json, name_file=name_file_2)
    new_list = []
    new_gamers = []

    def calculate_difference(new_val, old_val):
        return new_val - old_val if new_val - old_val > 0 else ""

    def update_field(gamer_data, field_name, new_value):
        change_field = f'change_{field_name}'
        if new_value != gamer_data[field_name]:
            if gamer_data[field_name] not in gamer_data[change_field]:
                gamer_data[change_field].append(gamer_data[field_name])
            if new_value in gamer_data[change_field]:
                gamer_data[change_field].remove(new_value)
            p_log(f"<{gamer_data['name']}> изменил {field_name} на <{new_value}>")
            gamer_data[field_name] = new_value
            return gamer_data[change_field]
        return gamer_data[change_field] if gamer_data[change_field] else ""

    for gamer_id in dct_new:
        if gamer_id in dct_old:
            old_data = dct_old[gamer_id]
            new_data = dct_new[gamer_id]

            # Обновляем данные
            change_name = update_field(old_data, 'name', new_data['name'])
            change_clan = update_field(old_data, 'clan', new_data['clan'])

            new_list.append([
                int(gamer_id),
                new_data['name'],
                new_data['clan'],
                new_data['level'],
                new_data['gold'],
                calculate_difference(new_data['level'], old_data['level']),
                calculate_difference(new_data['gold'], old_data['gold']),
                " ".join(change_name),
                " ".join(change_clan)
            ])
        else:
            p_log(f'Появился новый игрок: {gamer_id}: {dct_new[gamer_id]}')
            new_gamers.append(gamer_id)
            dct_old[gamer_id] = dct_new[gamer_id]

    if new_gamers:
        p_log(f"Новые игроки {new_gamers} будут добавлены в {name_file_old}")

    backup_json_file(path_json + name_file_old, backup_dir)
    save_json_file(dct_old, path_json, name_file_old)
    return new_list


if __name__ == "__main__":
    setup_logging()
    get_statistic()
    all_list = union_list(name_file_old, name_file_new)
    write_2dlist_to_excel(all_list, save_dir=excel_file_path)
