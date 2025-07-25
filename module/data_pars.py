import re
import setting

from bs4 import BeautifulSoup

from logs.logs import p_log
from module.all_function import remove_cyrillic, availability_id


def heals(resp):
    soup = BeautifulSoup(resp.text, 'lxml')
    try:
        life_count_element = int(soup.find(id="lifeCount").text.split()[0])
        p_log(f"Количество здоровья: {life_count_element}")
        return life_count_element
    except AttributeError:
        p_log("Ошибка получения здоровья", level='warning')


def pars_gold_duel(response, gold_info=False, all_info=False, win_status=False):
    soup = BeautifulSoup(response.text, 'lxml')
    fight_results = soup.find('div', class_='fightResultsInner')

    winner = fight_results.find('h1').text.strip()  # "name выйграл"
    result_gold = int(fight_results.find_all('em')[1].text)
    result_str = f"{winner}\n" + "\n".join(p.text.strip() for p in fight_results.find_all('p')) + "\n"

    if all_info:
        return result_gold, result_str
    if gold_info:
        return (result_gold, winner) if win_status else result_gold


def get_status_helper(response, type_helper):
    soup = BeautifulSoup(response.text, 'lxml')

    if type_helper == setting.type_helper_name[0]:
        item_helper = soup.find_all('div', id="itemHorse")
    else:
        item_helper = soup.find_all('div', id="itemCompanion")

    # Переменная для хранения результата
    result = None

    # Проверяем каждый найденный div
    for div in item_helper:
        inner_div = div.find('div')  # Ищем вложенный div
        if inner_div:
            # Извлекаем id и оставляем только цифры с помощью регулярного выражения
            result = ''.join(filter(str.isdigit, inner_div.get('id')))
            break

    return result


# Парсинг ключа 'description' - результат покупки зелья в событии "Лекарь"
def pars_healer_result(description_html):
    soup = BeautifulSoup(description_html, 'lxml')

    # Находим первый тег <td>
    td_tag = soup.find('td')

    if td_tag:
        # Находим первый тег <div> внутри <td>
        clean_text = td_tag.get_text(strip=True).replace("•", '')
        div_tag = td_tag.find('div')

        if div_tag and 'class' in div_tag.attrs:
            # Получаем список классов и берем первый элемент
            first_class = div_tag['class'][0]
            p_log(f"Вы получили {first_class}: {clean_text} штук")
        else:
            p_log(f"{clean_text}")


def get_all_silver(resp):
    soup = BeautifulSoup(resp.content, 'lxml')
    silver_count = int(soup.find(id='silverCount').text)
    return silver_count


def get_csrf_token(resp):
    content_type = resp.headers.get('Content-Type', '')
    if 'text/html' in content_type:
        soup = BeautifulSoup(resp.content, 'lxml')
        # Находим тег meta с нужным атрибутом
        meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})

        # Достаем значение атрибута content
        if meta_tag:
            csrf_token = meta_tag.get('content')
            return csrf_token
        else:
            p_log("Тег meta с именем 'csrf-token' не найден.", level='debug')


def get_title(resp):
    soup = BeautifulSoup(resp.content, 'lxml')
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else None
    return title


def check_cooldown_poit(html_page):
    """
    Функция проверяет таймер перезарядки использования зелья, повторно т.к. зелье можно использовать раз в 30 минут.
    Парсинг значения из g_potionCooldownCounter = new SimpleCountdown('.potionCooldown', 0)
    :param html_page: ответ get-запроса
    :return: таймер перезарядки в секундах
    """
    soup = BeautifulSoup(html_page.text, 'lxml')
    script_tags = soup.find_all('script')
    target_number = None

    for script in script_tags:
        if script.string:  # Проверяем, есть ли текст внутри тега script
            # Ищем нужную строку с помощью регулярного выражения
            match = re.search(r'g_potionCooldownCounter\s*=\s*new\s*SimpleCountdown\([^,]+\s*,\s*(\d+)\);',
                              script.string)
            if match:
                target_number = int(match.group(1))
                break

    return target_number


def set_name(resp):
    soup = BeautifulSoup(resp.content, 'lxml')
    title_tag = soup.find(class_="char-title")
    title = title_tag.get_text(strip=True) if title_tag else None
    if not title:
        raise Exception("Ошибка получения имени. Проверьте куки")
    setting.NAME = remove_cyrillic(title)  # Теперь это изменит глобальную переменную в модуле setting
    p_log(f"Добро пожаловать в игру, {setting.NAME}!")


def get_id(resp):
    soup = BeautifulSoup(resp.content, 'lxml')
    element = soup.find(id='shieldNeutral')
    url_profile = element.get('href') if element else None
    if not url_profile:
        raise Exception("Ошибка получения имени. Проверьте куки")
    match = re.search(r'/profile/(\d+)/', url_profile)
    user_id = match.group(1)

    if not availability_id(user_id):
        raise Exception("Доступ запрещен")


def pars_player(soup) -> dict:
    list_tr = {}
    for row in soup.find_all('tr')[3:]:
        list_td = []
        for i in row.find_all('td'):
            if not i.text.split():
                continue
            list_td.append(i.text.split()[-1])
        try:
            key = int(row.find(id='playerLink').get('href').split('/')[5])
        except Exception:
            raise "Ссылка на рыцаря не найдена. Проверить чередование 'tr'"
        link_tr = row.find_all(id='playerLink')
        if len(link_tr) == 2:
            name = remove_cyrillic(link_tr[0].text)
            clan = link_tr[1].text
        else:
            name = remove_cyrillic(link_tr[0].text)
            clan = ""
        value = {"name": name,
                 "clan": clan,
                 "level": int(list_td[2]),
                 "gold": int(list_td[3].replace('.', '')),
                 "fights": int(list_td[4].replace('.', '')),
                 "victory": int(list_td[5].replace('.', '')),
                 "defeats": int(list_td[6].replace('.', '')),
                 "change_name": [],
                 "change_clan": []}
        list_tr.setdefault(key, value)
    return list_tr
