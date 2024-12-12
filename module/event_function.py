from logs.logs import p_log
from module.all_function import no_cache
from module.game_function import get_item_loot
from module.http_requests import make_request
import random

from setting import CHRISTMAS_MODE


# __________________________________ Рождественский ивент ________________________________________
def christmas_bonus(func=None):
    if func is None:
        return lambda f: christmas_bonus(f)

    def wrapper(*args, **kwargs):
        p_log("Проверка рюкзака добычи на еду")
        bonus_items = get_item_loot('christmas')
        if bonus_items:
            bonus_item = random.choice(bonus_items)
            p_log("Попытка применить рожденственский баф на миссию")
            url_bonus = (f'https://s32-ru.battleknight.gameforge.com/ajax/ajax/'
                         f'activateQuestItem/{bonus_item}/lootbag?noCache={no_cache()}')
            try:
                resp = make_request(url_bonus).json()
                p_log(resp, level='debug')
                if resp['result']:
                    p_log('Баф активирован')
                else:
                    p_log(f"Баф не был активирован: {resp['reason']}, {resp['data']}", level='warning')
            except:
                p_log("Ошибка обработки запроса рожденственского бонуса", level='warning')
            get_item_loot('christmas')
        else:
            p_log("Еды в рюкзаке добычи не обнаружено")
        func(*args, **kwargs)

    return wrapper


def apply_christmas_bonus(func):
    if CHRISTMAS_MODE:
        return christmas_bonus(func)
    return func

# ________________________________________________________________________________________________
