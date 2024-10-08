from bs4 import BeautifulSoup

from game_play import put_gold
from module.all_function import no_cache
from module.http_requests import make_request, post_request

url_file = 'auctioneer.html'
url_auctioneer = 'https://s32-ru.battleknight.gameforge.com/market/auctioneer'
url_payout = 'https://s32-ru.battleknight.gameforge.com/treasury/payout'


def silver_count(soup) -> int:
    return int(soup.find(id='silverCount').text)


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


def payout(soup, silver_out: int):
    to_silver = silver_count(soup)
    payload = {'silverToPayout': silver_out}
    resp = post_request(url_payout, payload)
    after_silver = silver_count(BeautifulSoup(resp.text, 'lxml'))
    if after_silver - to_silver == silver_out:
        print(f"Из казны взято {silver_out} серебра")
        return after_silver
    else:
        print(f"Ошибка запроса взять из казны to_silver={to_silver}, after_silver={after_silver}")


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
    print(f"На руках {target_number} серебра")
    print(dct)

    if not dct:
        print("Нет колец на аукционе")
    else:
        min_key = min(dct, key=lambda k: int(dct[k]))
        min_value = int(dct[min_key])
        if min_value > target_number:
            need_silver = min_value - target_number
            print(f"Недостаточно серебра для ставки. Нужно еще {need_silver}")
            if need_silver < 500:
                after_silver = payout(soup, need_silver)
                place_bet(min_key, after_silver)
        else:
            print(f"Будет куплено кольцо с id={min_key}")
            place_bet(min_key, target_number)


if __name__ == "__main__":
    buy_ring()
    # put_gold()
