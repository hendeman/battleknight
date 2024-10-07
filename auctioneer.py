from bs4 import BeautifulSoup

from game_play import put_gold
from module.all_function import no_cache
from module.http_requests import make_request, post_request

url_file = 'auctioneer.html'
url_auctioneer = 'https://s32-ru.battleknight.gameforge.com/market/auctioneer'


def silver_count(soup):
    return soup.find(id='silverCount').text


def place_bet(id_item, bet):
    payload = {'noCache': no_cache()}
    resp = post_request(f'https://s32-ru.battleknight.gameforge.com/ajax/market/bid/{id_item}/{bet}', payload)
    try:
        if resp.json()['result']:
            print("Ставка выполнена успешно")
        else:
            print(f"Ошибка ставки, неверное количество серебра")
    except ValueError:
        print("Ошибка ставки. Ошибка json(). Неверный id_item")


def buy_ring():
    response = make_request(url_auctioneer)
    soup = BeautifulSoup(response.text, 'lxml')
    auction_item_box = soup.find_all('div', class_='auctionItemBox')
    # проверить "auctionItemBox" когда аукционер ничего не представил
    # print(len(auction_item_box))
    dct = {}
    for item in auction_item_box:
        # Находим нужный div с классом itemRing
        item_ring_div = item.find('div', class_=lambda x: x and x.startswith('itemRing'))
        if item_ring_div:
            # Извлекаем id
            id_item = item_ring_div['id'][8:]  # Обрезаем 'auctItem' для получения цифр

            # Находим input с нужным id
            bid_text_input = soup.find('input', id=f'bidText{id_item}')

            # Извлекаем значение value
            if bid_text_input:
                bid_value = bid_text_input['value']
                dct[id_item] = bid_value
    target_number = silver_count(soup)
    print(target_number)
    print(dct)
    max_value = None
    max_key = None

    # Проходим по элементам словаря
    for key, value in dct.items():
        if int(value) <= int(target_number):
            if max_value is None or value > max_value:
                max_value = value
                max_key = key
    if not max_key:
        print("Нет доступных колец в продаже")
    else:
        print(f"Будет куплено кольцо с id={max_key}")
        # place_bet(max_key, target_number)


if __name__ == "__main__":
    buy_ring()
    # put_gold()