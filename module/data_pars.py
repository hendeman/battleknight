import json
import re
import setting

from bs4 import BeautifulSoup

from logs.logs import p_log
from module.all_function import remove_cyrillic, availability_id, digi, save_error_html, no_cache


def pars_name(soup, user_tag=False):
    class_tag_name = 'char-title' if user_tag else 'profile-title'
    try:
        if user_tag:
            div_content = soup.find('div', class_=class_tag_name)
        else:
            div_content = soup.find('div', class_=class_tag_name).find('div')
        if div_content.br:
            # Получаем текст после <br>
            text_after_br = div_content.br.next_sibling
            if text_after_br:
                name = text_after_br.strip()
                return name
        return div_content.text()
    except AttributeError:
        p_log(f'Class {class_tag_name} not found for pars_name', level='warning')


def heals(resp):
    soup = BeautifulSoup(resp.text, 'lxml')
    try:
        life_count_element = int(soup.find(id="lifeCount").text.split()[0])
        p_log(f"Количество здоровья: {life_count_element}")
        return life_count_element
    except AttributeError:
        p_log("Ошибка получения здоровья", level='warning')


def is_horse_travel_button_active(resp, where):
    # проверка активности кнопки перемещения с помощью лошади
    # если не будет надет наездник, то кнопка будет "disabledBtn"
    soup = BeautifulSoup(resp.text, 'lxml')
    target_onclick = f"startTravel('{where}', 'horse', new Element(this), false);"
    a_tag = soup.find('a', attrs={'onclick': target_onclick})

    if a_tag:
        classes = a_tag.get('class', [])
        return 'disabledBtn' not in classes
    return False


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


def get_mission_point(soup):
    span_value = soup.select_one('p.missionPoints span')

    if span_value:
        value = span_value.get_text(strip=True)
        try:
            mission_point = int(value)
            return mission_point
        except ValueError:
            p_log(f"Не удалось преобразовать '{value}' в число", level='warning')
    else:
        p_log("Не удалось найти количество очком миссий", level='warning')


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
            save_error_html(resp)


def get_title(resp):
    soup = BeautifulSoup(resp.content, 'lxml')
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else None
    return title


def pars_treasury(resp):
    """
    Функция парсинга казны со страницы url_treasury = '/treasury'
    :param resp: response по url_treasury
    :return: (int, int)
    """
    soup = BeautifulSoup(resp.content, 'lxml')
    # Находим все em элементы в форме
    all_em = soup.select('#mailInbox .formLine em')

    # Берем первый и четвертый em (нужные нам значения)
    value1 = int(all_em[0].text)  # баланс серебра
    value2 = int(all_em[3].text)  # серебро в казне
    return value1, value2


def pars_stats(resp):
    """
    Функция парсинга атрибутов со страницы url_user = '/user/'
    :param resp: response по url_user
    :return: словарь вида {"str": value, "dex": value, "end": value, "luck": value, "weapon": value, "defense": value}
    """
    soup = BeautifulSoup(resp.content, 'html.parser')

    table = soup.find('table', id='charAttTable1')
    rows = table.find_all('tr')
    data = {}

    for row, key in zip(rows, setting.ATTRIBUTES):
        cost_td = row.find('td', class_='attrCost')
        if cost_td:
            cost_value = int(cost_td.get_text(strip=True))
            data[key] = cost_value
    return data


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
    setting.NAME = pars_name(soup, user_tag=True)  # Теперь это изменит глобальную переменную в модуле setting
    p_log(f"Добро пожаловать в игру, {setting.NAME}!")


def get_id(resp, not_token=False):
    soup = BeautifulSoup(resp.content, 'lxml')
    bubble = soup.find(id='bubble')
    element = soup.find(id='shieldNeutral')
    url_profile = element.get('href') if element else None
    if not url_profile and not bubble:
        raise Exception("Ошибка получения имени. Проверьте куки")
    if bubble:
        from module.http_requests import make_request
        from setting import SERVER, url_user
        p_log("Есть bubble блок")
        bubble_url_reset = f'{SERVER}/ajax/user/hideLevelupHint/?{no_cache()}'
        response = make_request(bubble_url_reset)
        if not response.json():
            p_log("bubble return False")
            user_id = 'bubble'
        else:
            response = make_request(url_user)
            get_id(response, not_token=not_token)
            return
    else:
        match = re.search(r'/profile/(\d+)/', url_profile)
        user_id = match.group(1)

    if not availability_id(user_id, not_token):
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


# __________________________________ Парсинг надетых компаньона и наездника по ID ______________________
def find_item_data(soup, target_item_id):
    script_tags = soup.find_all('script')

    for script in script_tags:
        if script.string:  # Проверяем, что тег script содержит текст
            # Ищем все вызовы g_dragFunctions.storeAttributes в тексте скрипта
            matches = re.finditer(
                r'g_dragFunctions\.storeAttributes\((.+?)\);',
                script.string,
                re.DOTALL
            )
            for match in matches:
                # Пытаемся разобрать аргументы функции
                args_text = match.group(1)
                # Разделяем аргументы, учитывая вложенные структуры
                args = split_args(args_text)

                # Последний аргумент должен быть словарем
                if len(args) >= 9:  # Проверяем, что аргументов достаточно
                    try:
                        last_arg = args[-1]
                        # Очищаем JSON от возможных лишних символов
                        data = json.loads(last_arg)

                        # Проверяем совпадение item_id
                        if str(data.get('item_id')) == str(target_item_id):
                            return {
                                'item_id': data.get('item_id'),
                                'item_fullName': data.get('item_fullName'),
                                'item_pic': data.get('item_pic'),
                                'speed_travel': data.get('item_special_ability').get('HorseTravelTimeReduction', 0)
                                if data.get('item_special_ability')
                                else 0,
                                'item_use': int(data.get('item_use', 0)),
                                'item_expires': data.get('item_expires')
                            }
                    except json.JSONDecodeError:
                        continue  # Пропускаем некорректные JSON
    return None


def split_args(args_text):
    # Функция для разделения аргументов, учитывая вложенные структуры
    args = []
    current_arg = []
    brace_level = 0
    bracket_level = 0
    quote_char = None
    escape = False

    for char in args_text.strip():
        if escape:
            current_arg.append(char)
            escape = False
            continue

        if char == '\\':
            escape = True
            current_arg.append(char)
            continue

        if char == '"' or char == "'":
            if quote_char is None:
                quote_char = char
            elif quote_char == char:
                quote_char = None
            current_arg.append(char)
        elif quote_char is not None:
            current_arg.append(char)
        else:
            if char == '{':
                brace_level += 1
            elif char == '}':
                brace_level -= 1
            elif char == '[':
                bracket_level += 1
            elif char == ']':
                bracket_level -= 1

            if char == ',' and brace_level == 0 and bracket_level == 0:
                args.append(''.join(current_arg).strip())
                current_arg = []
            else:
                current_arg.append(char)

    if current_arg:
        args.append(''.join(current_arg).strip())

    return args


def get_karma_value(soup):
    """ Возвращает значение кармы """
    karma_element = soup.find('span', class_='icon iconKarmaGood')
    if karma_element:
        karma_value = karma_element.parent.text.strip()
        return int(karma_value)


def get_point_mission(soup):
    point_mission = soup.find('span', id='zoneChangeCosts')
    if point_mission:
        return point_mission.text.strip()
    p_log(f"Ошибка получения данных очков миссий", level='warning')


# _____________________________________ Парсинг последней активности игрока в ордене _________________________________
def visit(soup) -> dict:
    new = []
    lst = soup.find_all('script')[-2].text.replace("\n", "").replace(" ", "").split(";")
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
            if not i.get_text(strip=True):
                continue
            if i.get('class') and i.get('class')[0] == 'memberRank':
                selected_option = i.find('option', selected=True)
                list_td.append(selected_option.get('value') if selected_option else i.get_text(strip=True))
            else:
                list_td.append(i.get_text(strip=True))

        key = row.attrs['id'].replace("recordMember", "")
        value = {"name": remove_cyrillic(list_td[1]),
                 "level": int(list_td[2]),
                 "gold": int(list_td[3].replace(".", "")),
                 "rank": list_td[0] if list_td[0].isdigit() else '1'}
        list_tr.setdefault(key, value)

    return list_tr
