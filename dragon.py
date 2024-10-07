from colorama import Fore
from bs4 import BeautifulSoup

from logs.logs import p_log
from module.all_function import time_sleep
from module.data_pars import heals
from module.http_requests import post_request, make_request
from setting import castles_all, castles_island, castles, status_list

world_url = 'https://s4-ru.battleknight.gameforge.com/world'
post_url = 'https://s4-ru.battleknight.gameforge.com/world/location/'
map_url = 'https://s4-ru.battleknight.gameforge.com/world/map'
travel_url = 'https://s4-ru.battleknight.gameforge.com:443/world/startTravel'
mission_url = 'https://s4-ru.battleknight.gameforge.com/world/location'


def post_travel(out='', where='', how='horse'):
    payload = {
        'travelwhere': f'{where}',
        'travelhow': f'{how}',
        'travelpremium': 0
    }
    p_log(payload)
    print_status(out, where, how)
    post_request(travel_url, payload)

    check_timer()


def post_dragon(buy_rubies=''):
    payload = {
        'chooseMission': 'DragonEventGreatDragon',
        'missionArt': 'large',
        'missionKarma': 'Good',
        'buyRubies': f"{buy_rubies}"
    }

    post_request(post_url, payload)
    p_log(f"Атака выполнена успешно, потрачено {buy_rubies if buy_rubies else '0'} рубинов")

    check_timer()


def process_page(url):
    break_outer = False
    response = make_request(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    a_tags = soup.find_all('a', onclick=lambda
        onclick: onclick and "chooseMission('large', 'DragonEventGreatDragon', 'Good', this)" in onclick)

    if a_tags:
        for a_tag in a_tags:
            if 'disabledSpecialBtn' in a_tag.get('class', []):
                buy_rubies_tags = soup.find_all('a', class_='devLarge missionBuyRubies toolTip',
                                                onclick=lambda onclick: onclick and (
                                                        "chooseMission('large', 'DragonEventGreatDragon', 'Good', this, '1')" in onclick
                                                        or "chooseMission('large', 'DragonEventGreatDragon', 'Good', this, '2')" in onclick
                                                        or "chooseMission('large', 'DragonEventGreatDragon', 'Good', this, '3')" in onclick))
                if buy_rubies_tags:
                    for buy_rubies_tag in reversed(buy_rubies_tags):
                        onclick_value = buy_rubies_tag.get('onclick')
                        p_log(onclick_value)
                        if onclick_value:
                            parts = onclick_value.split(',')
                            if len(parts) > 4:
                                fifth_argument = parts[4].strip().strip("');")

                                post_dragon(buy_rubies=fifth_argument)
                                break_outer = True
                                break
                    if break_outer:
                        break
        else:
            post_dragon()
    else:
        p_log('Не удалось найти тег <a> с нужным атрибутом onclick.')


def my_place():
    response = make_request(mission_url)
    soup = BeautifulSoup(response.text, 'lxml')
    place = soup.find('h1').text.strip()
    for key, value in castles_all.items():
        if value == place:
            return value, key
    return place, None


def check_timer():
    response = make_request(mission_url)
    soup = BeautifulSoup(response.text, 'lxml')
    response = soup.find('h1').text.strip()
    if response in status_list:
        timer = soup.find(id="progressbarEnds").text.strip()
        hours, minutes, seconds = map(int, timer.split(':'))
        extra_time = 10
        total_seconds = hours * 3600 + minutes * 60 + seconds + extra_time
        p_log(Fore.YELLOW + f" lupatik статус <{response}>" + Fore.RESET)
        time_sleep(total_seconds)


def print_status(from_town, where_town, how):
    p_log(Fore.GREEN +
          f" {'Едем' if how == 'horse' else 'Плывем'} из {castles_all[from_town]} в {castles_all[where_town]}"
          + Fore.RESET)


def dragon_search():
    place, my_town = my_place()  # Джаро, VillageFour
    p_log(f"Я нахожусь в {place}")
    response = make_request(map_url)
    soup = BeautifulSoup(response.text, 'lxml')
    dragon_town = soup.find(id="DragonIcon").get('class')[0]
    if not dragon_town:
        raise "Дракона нет на карте"
    p_log(f"Дракон находится в {castles_all[dragon_town]}")

    if (my_town in castles_island and dragon_town in castles_island) or (my_town in castles and dragon_town in castles):
        if my_town == dragon_town:
            p_log(Fore.RED + f" Вы в городе с драконом!" + Fore.RESET)
            while True:
                response = make_request(map_url)
                if heals(response) < 20:
                    p_log(Fore.YELLOW + "Отдыхаем 10 минут, пока не восстановится здоровье" + Fore.RESET)
                    time_sleep(610)
                else:
                    break
            process_page(world_url)  # атака на дракона
        else:
            post_travel(out=my_town, where=dragon_town)

    if my_town in castles_island and dragon_town in castles:
        if my_town == 'HarbourTwo':
            post_travel(out='HarbourTwo', where='HarbourOne', how='cog')
        else:
            post_travel(out=my_town, where='HarbourTwo')

    if my_town in castles and dragon_town in castles_island:
        if my_town == 'HarbourOne':
            post_travel(out='HarbourOne', where='HarbourTwo', how='cog')
        else:
            post_travel(out=my_town, where='HarbourOne')


if __name__ == "__main__":
    check_timer()
    while True:
        dragon_search()
# process_page(url)
# check_timer()
# post_travel(where='HarbourTwo', how='horse')
