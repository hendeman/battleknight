import time

from bs4 import BeautifulSoup
import re

from logs.logs import p_log
from module.all_function import no_cache, format_time, get_config_value
from module.http_requests import make_request, post_request

# Регулярное выражение для поиска
pattern = re.compile(r'acquireMerc\d+npc')


def calculate_sum(num_list):
    total = 0
    for item in num_list:
        if ' - ' in item:  # Проверяем, есть ли диапазон
            # Разделяем диапазон и вычисляем среднее
            start, end = map(int, item.split(' - '))
            average = (start + end) / 2
            total += average
        else:
            # Преобразуем строку в число и добавляем к сумме
            total += int(item)
    return total


url_group = 'https://s32-ru.battleknight.gameforge.com/groupmission'
url_group_members = 'https://s32-ru.battleknight.gameforge.com/groupmission/groupMembers'
url_group_pas = 'https://s32-ru.battleknight.gameforge.com/groupmission/dice'
url_group_delete = 'https://s32-ru.battleknight.gameforge.com/groupmission/deleteGroup'


def create_group():
    payload = {
        'name': 'меня нет',
        'minLevel': 29,
        'maxLevel': 48,
        'maxMember': 2,
        'plandata': 'hard',
        'onlyApply': 0,
        'onlyOrder': get_config_value("only_order")
    }
    make_request(url_group)
    time.sleep(1)
    try:
        result = post_request('https://s32-ru.battleknight.gameforge.com/groupmission/foundGroup/', payload).json()
        if result:
            p_log("Группа успешно создана")
            return True
        else:
            p_log("Ошибка создания группы. Проверьте post-запрос")
    except ValueError:
        p_log("Группа не может быть создана. Ошибка json(). Возможные причины: занят, не хватает очков", level='warning')


def hire_mercenary(id_mercenary):
    resp = make_request(
        f"https://s32-ru.battleknight.gameforge.com/groupmission/addNPC/{id_mercenary}?noCache={no_cache()}")
    try:
        if resp.json()['result']:
            p_log("Наёмник успешно нанят")
            return True
        else:
            p_log(f"Ошибка найма. Неверный {id_mercenary}")
    except ValueError:
        p_log("Ошибка найма. Ошибка json()", level='warning')


def pas_group():
    make_request(url_group)  # попробуй url_group_pas
    time.sleep(2)
    payload = {'dicePassValue': 1}
    post_request(url_group_pas, payload)
    p_log("Запрос на ПАС группы выполнен")
    time.sleep(2)
    return BeautifulSoup(make_request(url_group).text, 'lxml').text


def delete_group():
    make_request(url_group_delete)
    p_log("Группа удалена")


def get_mercenary():
    response = make_request(url_group_members)
    soup = BeautifulSoup(response.text, 'lxml')
    try:
        table = soup.find('table', id="mercenaryTable")

        # Поиск всех ссылок с id=acquireMerc{numbers}npc и выделение numbers
        matches = [''.join(filter(lambda a: a.isdigit(), x['id'])) for x in table.find_all('a', id=pattern)]
        print(matches)
        attr_sum = []
        profile_table = table.find_all('table', {'class': 'profileTable'})
        for i in profile_table:
            attr_list = [x.text.strip() for x in i.find_all('td')]
            attr_sum.append(calculate_sum(attr_list))
        print(attr_sum)
        if len(matches) != len(attr_sum):
            with open('group.html', 'w', encoding='utf-8') as file:
                file.write(soup.text)
            raise AttributeError(f"Количество id={len(matches)} должно быть равно количеству attr={len(attr_sum)}")
        if max(attr_sum) < 1500:
            p_log("В группе слишком слабые наёмники. Группа будет пересоздана")
            return False
        strong_mercenary = matches[attr_sum.index(max(attr_sum))]
        print(strong_mercenary)
        return strong_mercenary
    except Exception as s:
        p_log(f"Ошибка парсинга в группе. Группа будет удалена. {s}", level='warning')
        return s


def go_group(time_wait=0):
    if create_group():
        if time_wait:
            p_log(f"Ожидание игроков для группы {format_time(time_wait)} ...")
        time.sleep(time_wait)
        if "К сожалению, у вас недостаточно очков миссий" in pas_group():
            p_log("Группа успешно завершена с игроком")
        else:
            while True:
                mercenary = get_mercenary()
                time.sleep(4)
                if not mercenary:
                    delete_group()
                    time.sleep(2)
                    if not create_group():
                        break
                elif isinstance(mercenary, Exception):
                    delete_group()
                    break
                else:
                    if hire_mercenary(mercenary):
                        break
                    else:
                        delete_group()
                        break


if __name__ == "__main__":
    go_group(5400)