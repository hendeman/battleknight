import time
from functools import partial
from json import JSONDecodeError

from bs4 import BeautifulSoup
import re

from logs.logs import p_log

from module.all_function import no_cache, format_time, get_config_value, time_sleep, call_parameters, save_error_html
from module.game_function import check_progressbar
from module.http_requests import make_request, post_request
from setting import SERVER, url_group, url_greate_group, url_group_pas, url_group_delete, url_group_members, \
    url_join_group, url_refresh_groups

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


def create_group():
    gm_param = get_config_value(key=("gm_name", "gm_max_member", "gm_plandata", "gm_only_order"))
    payload = {
        'name': gm_param.get("gm_name"),
        'minLevel': 29,
        'maxLevel': 48,
        'maxMember': gm_param.get("gm_max_member"),
        'plandata': gm_param.get("gm_plandata"),
        'onlyApply': 0,
        'onlyOrder': gm_param.get("gm_only_order")
    }
    p_log(payload, level='debug')
    make_request(url_group)
    time.sleep(1)
    try:
        result = post_request(url_greate_group, payload).json()
        if result['result']:
            p_log("Группа успешно создана")
            return True
        else:
            p_log("Ошибка создания группы. Проверьте post-запрос")
            p_log(result, level='debug')
    except ValueError:
        p_log("Группа не может быть создана. Ошибка json(). Возможные причины: занят, не хватает очков",
              level='warning')


def hire_mercenary(id_mercenary):
    resp = make_request(f"{SERVER}/groupmission/addNPC/{id_mercenary}?noCache={no_cache()}")
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
    post_request(url_group_pas, payload, csrf=False)
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


@call_parameters
def go_group(time_wait: int = partial(get_config_value, key='group_wait')):
    if create_group():
        if time_wait:
            p_log(f"Ожидание игроков для группы {format_time(time_wait)} ...")
        time.sleep(time_wait)
        time_sleep(check_progressbar())
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


def find_group(knight_id):
    """
    Поиск созданной группы по ID игрока
    :param knight_id: ID игрока
    :return: ID группы или None
    """
    resp = None
    make_request(url_group)
    body = {'sortBy': 'Level',
            'sortMode': 'down',
            'page': 0,
            'name': '',
            'onlyNotApply': 0,
            'onlyOrder': 0}

    url_find = (f'{url_refresh_groups}/?sortBy={body["sortBy"]}'
                f'&sortMode={body["sortMode"]}&page={body["page"]}&name={body["name"]}'
                f'&onlyNotApply={body["onlyNotApply"]}&onlyOrder={body["onlyOrder"]}')
    try:
        resp = post_request(url_find, body).json()
        if resp["result"]:
            entries = resp["data"]["entries"]
            if entries:
                for gr in entries:
                    if str(gr.get('knight_id')) == knight_id:
                        return str(gr.get('grp_id'))
            else:
                p_log('Нет созданных групп')
        else:
            p_log(f"Ошибка запроса поиска группы: {resp}")
    except JSONDecodeError:
        p_log('Ошибка в find_group: получен не JSON-ответ от сервера', level='warning')
        save_error_html(resp)


def join_group(creator_id, retryer=6, refresh_seconds=300):
    """
    Присоединение к группе с creator_id. Поиск по параметрам.
    :param creator_id: ID создателя группы
    :param retryer: Количество попыток обновления поиска группы
    :param refresh_seconds: Пауза между попытками обновления поиска группы
    :return: None
    """
    check_progressbar()
    while retryer:
        grp_id = find_group(creator_id)
        if grp_id:
            url_join = f'{url_join_group}{grp_id}'
            body = {'groupID': grp_id}
            post_request(url_join, body)
            make_request(url_group)
            retryer = 0
        else:
            retryer -= 1
            time_sleep(refresh_seconds)
    timer_group = check_progressbar()
    if timer_group:
        p_log(f"Ожидание после группы {format_time(timer_group)}. Ожидаем...")
        time_sleep(timer_group)


if __name__ == "__main__":
    go_group(5400)
