import time

from bs4 import BeautifulSoup
import re

from module.all_function import no_cache
from module.http_requests import make_request, post_request
from sliv import make_attack

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
        'onlyOrder': 1
    }
    make_request(url_group)
    time.sleep(1)
    try:
        result = post_request('https://s32-ru.battleknight.gameforge.com/groupmission/foundGroup/', payload).json()
        if result:
            print("Группа успешно создана")
            return True
        else:
            print("Ошибка создания группы. Проверьте post-запрос")
    except ValueError:
        print("Группа не может быть создана. Ошибка json(). Возможные причины: занят, не хватает очков")


def hire_mercenary(id_mercenary):
    resp = make_request(
        f"https://s32-ru.battleknight.gameforge.com/groupmission/addNPC/{id_mercenary}?noCache={no_cache()}")
    try:
        if resp.json()['result']:
            print("Наёмник успешно нанят")
            return True
        else:
            print(f"Ошибка найма. Неверный {id_mercenary}")
    except ValueError:
        print("Ошибка найма. Ошибка json()")


def pas_group():
    make_request(url_group)  # попробуй url_group_pas
    time.sleep(2)
    payload = {'dicePassValue: ': 1}
    post_request(url_group_pas, payload)
    print("Запрос на ПАС группы выполнен")
    time.sleep(2)
    make_request(url_group)


def delete_group():
    make_request(url_group_delete)
    print("Группа удалена")


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
            print("В группе слишком слабые наёмники. Группа будет пересоздана")
            return False
        strong_mercenary = matches[attr_sum.index(max(attr_sum))]
        print(strong_mercenary)
        return strong_mercenary
    except Exception as s:
        print("Ошибка парсинга в группе. Группа будет удалена.", s)
        return s


def go_group(time_wait=0):
    if create_group():
        time.sleep(time_wait)
        pas_group()
        # сюда нужно вписать ожидание час и проверку на то что группа пройдена ну и pas_group() перед проверкой
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
    # go_group()
    # create_group()
    # pas_group()
    # когда будет кнопка пас, то проверить ссылку https://s32-ru.battleknight.gameforge.com/groupmission/group/
    # проверить вручную нападание через ссылку и посмотреть теги h4 и h3
    # попробовать перейти по ссылке рыцаря и прочитать надпись на дуэли
    make_attack('916540', heals_point=False)
