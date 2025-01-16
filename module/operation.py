import os
import pickle
import re

import requests
from bs4 import BeautifulSoup

from module.all_function import remove_cyrillic, day, syntax_day
from setting import exclusion_list, url_members, cookies, headers, url_name, FILE_NAME, deco_func, today

GOLD_DAY = 100


def digi(bad_string: str) -> int:
    return int(re.findall(r'\b\d+\b', bad_string)[0])


def visit(soup) -> dict:
    new = []
    lst = soup.find_all('script')[-1].text.replace("\n", "").replace(" ", "").split(";")
    for i in lst:
        if "}" in i:
            break
        new.append(i)

    if len(new) % 3 != 0:
        raise "Ошибка парсинга <script> данных"

    del new[2::3]
    new_lst = dict([(str(digi(x)), digi(y)) for x, y in zip(new[::2], new[1::2])])
    # return dict(filter(lambda item: item[1] <= 3, new_lst.items()))
    return new_lst


def party(soup) -> dict:
    list_tr = {}
    for row in soup.find('table', id='membersTable').find_all('tr')[1:]:
        list_td = []
        for i in row.find_all('td'):
            if not i.text.split():
                continue
            list_td.append(i.text.replace('\n', '').strip())

        key = row.attrs['id'].replace("recordMember", "")
        value = {"name": remove_cyrillic(list_td[1]), "level": int(list_td[2]),
                 "gold": int(list_td[3].replace(".", ""))}
        list_tr.setdefault(key, value)

    return list_tr


def all_party(a: dict, b: dict) -> dict:
    all_dct_new = {}
    for x, y in zip(a.items(), b.items()):
        y[1]["time"] = x[1]
        all_dct_new.setdefault(x[0], y[1])
    return all_dct_new


def exclude_keys_decorator(exclusion_list=None, deco_func=False):
    def decorator(func):
        def wrapper(dict1, dict2):
            dict3 = func(dict1, dict2)
            if exclusion_list:
                for key in exclusion_list:
                    dict3.pop(key, None)
            return dict3

        return wrapper if deco_func else func  # Возвращаем обертку или саму функцию

    return decorator


# Декоратор exclude_keys_decorator добавляет список исключения exclusion_list = ["Ksusha"]
@exclude_keys_decorator(exclusion_list=exclusion_list, deco_func=deco_func)
def replenish_treasury(a: dict, b: dict) -> dict:
    # Функция для обновления ордена
    def update_order(a, b, add_message=None, remove_message=None):
        if add_message:
            knight_names = [a[x]["name"] for x in set(a).difference(set(b))]
            print(f'Добро пожаловать в орден {", ".join(knight_names)}')
        if remove_message:
            knight_names = [b[x]["name"] for x in set(b).difference(set(a))]
            print(f'Рыцарь {", ".join(knight_names)} вышел из ордена')

        for i in set(a).difference(set(b)):
            b[i] = a[i]
            b[i]["gold"] = 0

    # Проверка и обновление ордена
    if len(a) < len(b):
        update_order(a, b, None, 'Рыцарь вышел из ордена')

    elif len(a) > len(b):
        update_order(a, b, 'Добро пожаловать в орден', None)

    elif len(set(a).intersection(set(b))) < len(b):
        update_order(a, b, 'Добро пожаловать в орден', 'Рыцарь вышел из ордена')

    return {value["name"]: {"gold": (lambda x, y: x - y if x - y >= 0 else x)(value["gold"], b[key]["gold"]),
                            "level": value["level"]}
            for key, value in a.items()
            if value["time"] <= 4}


def get_gold_day():
    global GOLD_DAY
    url_clan = 'https://s32-ru.battleknight.gameforge.com/clan/upgrades'
    resp = requests.get(url_clan, cookies=cookies, headers=headers)
    pattern = r'"payments":(\d+)'
    match = re.search(pattern, resp.text)
    if match:
        payments_value = int(match.group(1))  # Получаем полное соответствие
        GOLD_DAY = payments_value


def gold_factor(a: dict, pas_day: int) -> dict:
    pas_day = 1 if pas_day == 0 else pas_day
    total_levels_sum = sum(map(lambda x: x['level'], a.values()))
    factor = round(GOLD_DAY / total_levels_sum, 2)
    return {key: {'gold': value['gold'],
                  'kg': int((value["gold"] * 100 / pas_day) / (value["level"] * factor)),
                  'balance': int(value['gold'] - value["level"] * factor * pas_day),
                  'level': value["level"]} for
            key, value in a.items()}


def print_data(ss, debet, credit, days_have_passed, write_flag):
    pref = "_all" if write_flag else ""
    txt_report = f"bk\\report_clan\\report_{today.day:02d}_{today.month:02d}{pref}.txt"
    try:
        os.makedirs(os.path.dirname(txt_report), exist_ok=True)
        with open(txt_report, 'w', encoding='utf-8') as file:
            file.write(f"""Статистика пополнения казны за {days_have_passed} {syntax_day(days_have_passed)}.
Всего сдано {debet} золота. Потрачено куклой {credit} золота.
Итого: {'+' if debet - credit >= 0 else ''}{debet - credit}
Меценатом недели становится {list(ss.keys())[0]} !!!\n""")
            for i in ss.items():
                file.write(
                    f"{i[1]['gold']:6} | {['', '+'][i[1]['balance'] >= 0]}{i[1]['balance']} золота → {i[0]} {i[1]['level']}ур. ({i[1]['kg']} %)\n")
            file.write("""Всего пополнил в казну | +избыток, -недосдача → имя (KZ %)
KZ - соотношение между внесенным в казну золотом и необходимым (в процентах)""")
            print(f"Отчет {txt_report} успешно создан")
    except:
        print(f"Ошибка записи {txt_report}")


def get_statistic_clan(write_flag):
    resp = requests.get(url_members, cookies=cookies, headers=headers)
    os.makedirs(os.path.dirname(url_name), exist_ok=True)
    with open(url_name, 'w', encoding='utf-8') as file:
        file.write(resp.text)

    with open(url_name, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'lxml')

        time_visit_number, party_gold = visit(soup), party(soup)

        if len(time_visit_number) != len(party_gold):
            raise f"Нет совпадения длины списков: {len(time_visit_number)}!={len(party_gold)}"
        all_dct = all_party(time_visit_number, party_gold)

        with open(FILE_NAME, 'rb') as f:
            loaded_dict = pickle.load(f)
            days_have_passed = day(FILE_NAME)  # количество дней для статистики int

            dc = gold_factor(replenish_treasury(all_dct, loaded_dict),
                             days_have_passed)  # Коэфф. Золота(сравнить два словаря)

            ss = dict(sorted(dc.items(), key=lambda item: item[1]["balance"], reverse=True))
            debet, credit = sum(map(lambda x: x['gold'], ss.values())), days_have_passed * GOLD_DAY

            print_data(ss, debet, credit, days_have_passed, write_flag)  # вывести данные в консоль, создание отчета report.txt

        return all_dct


get_gold_day()
