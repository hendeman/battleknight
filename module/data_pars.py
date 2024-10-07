from bs4 import BeautifulSoup

from logs.logs import p_log


def heals(resp):
    soup = BeautifulSoup(resp.text, 'lxml')
    try:
        life_count_element = int(soup.find(id="lifeCount").text.split()[0])
        p_log(f"Количество здоровья: {life_count_element}")
        return life_count_element
    except Exception:
        p_log("Error parsing current health", level='warning')


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


def get_status_horse(response):
    soup = BeautifulSoup(response.text, 'lxml')

    # Находим все div с id="itemHorse"
    item_horse = soup.find_all('div', id="itemHorse")

    # Переменная для хранения результата
    result = None

    # Проверяем каждый найденный div
    for div in item_horse:
        inner_div = div.find('div')  # Ищем вложенный div
        if inner_div:
            # Извлекаем id и оставляем только цифры с помощью регулярного выражения
            result = ''.join(filter(str.isdigit, inner_div.get('id')))
            break

    return result
