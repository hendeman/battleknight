from datetime import date
import os
import json
from dotenv import load_dotenv

load_dotenv()

today = date.today()

CHRISTMAS_MODE = False

GOLD_DAY = 25090
GOLD_LIMIT = 7000
CURRENT_TAX = 0.6
waiting_time = 600
start_game = "09:00"

# Выбор программы:
# 1 - это программа клановой статистики
# 0 - это программа серверной статистики
program_selection = 0

# Сохранение данных в pickle-файл
write_flag = False

# Исключить имя из статистики вкл/выкл режима. Список исключений
deco_func = False
exclusion_list = ["Ksusha", "kimbow"]

FILE_NAME = "pickles_data/all_dct.pickle"
STAT_FILE_NAME = "pickles_data/stat_dct.pickle"
STAT_FILE_LOSS = 'pickles_data/loss.pickle'
GOLD_GAMER = 'pickles_data/gamer_gold.pickle'
NICKS_GAMER = 'pickles_data/nicks.pickle'
SAVE_CASTLE = 'pickles_data/save_castle.pickle'
filename = 'config.ini'
url_nicks = "nicksflower.txt"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br'
}

cookies_str = os.getenv('COOKIES')
cookies = json.loads(cookies_str) if cookies_str else {}

castles_island = {'VillageFour': 'Джаро', 'FortressTwo': "Сёгур", 'HarbourTwo': "Альван", 'TradingPostFour': 'Милей'}
castles = {'CityOne': "Алкран", 'CoastalFortressOne': "Асгал", 'CoastalFortressTwo': "Гастайн",
           'FortressOne': "Тулгар",
           'GhostTown': "Талфур",
           'HarbourOne': "Вейл", 'HarbourThree': "Седвич",
           'CapitalCity': "Эндалайн",
           'TradingPostOne': "Гранд", 'TradingPostTwo': "Талмет", 'TradingPostThree': "Брент",
           'VillageOne': "Терент", 'VillageTwo': "Хатвиг", 'VillageThree': "Рамстилл"}
castles_all = {**castles, **castles_island}
auction_castles = ('HarbourThree', 'TradingPostOne', 'CapitalCity', 'TradingPostTwo',
                   'HarbourOne', 'TradingPostThree', 'VillageThree', 'CityOne',
                   'HarbourTwo', 'TradingPostFour')
status_list = ['Ожидание после дуэли', 'Ожидание после миссии', 'Путешествие', 'Работа', 'Рынок']
status_list_eng = ['Ozhidanie posle dueli', 'Ozhidanie posle missii', 'Puteshestvie', 'Rabota', 'Rynok']
mount_list = {'pegasus': {'id_helper': '16888797', 'type_helper': 'horse', 'name': '<Пегас>'},
              'bear': {'id_helper': '16896645', 'type_helper': 'horse', 'name': '<Боевой медведь>'},
              'boar': {'id_helper': '17561824', 'type_helper': 'horse', 'name': '<Дикий кабан>'},
              'unicorn': {'id_helper': '16459963', 'type_helper': 'horse', 'name': '<Белый единорог>'},
              'squire': {'id_helper': '15959290', 'type_helper': 'companion', 'name': '<Сквайр>'},
              'rabbit': {'id_helper': '15517097', 'type_helper': 'companion', 'name': '<Кролик>'},
              'dog': {'id_helper': '16459964', 'type_helper': 'companion', 'name': '<Ищейка>'},
              'fairy': {'id_helper': '18884016', 'type_helper': 'companion', 'name': '<Фея Света>'}}
start_time = ['09:00', '15:25', '22:40']
potion_name = ['itemPotionRed50', 'itemPotionRed100', 'itemPotionRed200', 'itemPotionBlue300', 'itemPotionBlue500',
               'itemPotionYellowFull', 'itemPotionKarmaSwitch']
potion_name_buy = ['itemPotionRed50', 'itemPotionRed100', 'itemPotionRed200']

# _____________________________________ Игровые ссылки _____________________________________________
url_members = 'https://s32-ru.battleknight.gameforge.com/clan/members'
url_gold = 'https://s32-ru.battleknight.gameforge.com/clan/upgrades'
url_stat = 'https://s32-ru.battleknight.gameforge.com:443/highscore/'
world_url = 'https://s32-ru.battleknight.gameforge.com/world'
map_url = 'https://s32-ru.battleknight.gameforge.com/world/map'
url_compare = 'https://s32-ru.battleknight.gameforge.com/duel/compare/?enemyID='
url_duel_name = "https://s32-ru.battleknight.gameforge.com/duel/duel/?enemyID="
url_group = 'https://s32-ru.battleknight.gameforge.com/groupmission/group/'
url_orden_message = "https://s32-ru.battleknight.gameforge.com/ajax/board/sendmessage"
url_ordermail = "https://s32-ru.battleknight.gameforge.com/mail/ordermail"
url_error = "https://s32-ru.battleknight.gameforge.com:443/common/error"
travel_url = 'https://s32-ru.battleknight.gameforge.com:443/world/startTravel'
mission_url = 'https://s32-ru.battleknight.gameforge.com/world/location'
post_url = 'https://s32-ru.battleknight.gameforge.com/world/location/'
url_world = 'https://s32-ru.battleknight.gameforge.com/world/travel'
healer_url = 'https://s32-ru.battleknight.gameforge.com/zanyhealer/buyAndUsePotion/'
url_market = 'https://s32-ru.battleknight.gameforge.com/market/merchant/artefacts'
url_loot = 'https://s32-ru.battleknight.gameforge.com/user/loot/'
work_url = 'https://s32-ru.battleknight.gameforge.com:443/market/work'
treasury_url = 'https://s32-ru.battleknight.gameforge.com/treasury'
deposit_url = 'https://s32-ru.battleknight.gameforge.com/treasury/deposit'
user_url = 'https://s32-ru.battleknight.gameforge.com/user/'
point_url = 'https://s32-ru.battleknight.gameforge.com/user/getPotionBar'
url_auctioneer = 'https://s32-ru.battleknight.gameforge.com/market/auctioneer'
url_payout = 'https://s32-ru.battleknight.gameforge.com/treasury/payout'
duel_url = 'https://s32-ru.battleknight.gameforge.com/duel/'
url_joust_sign = 'https://s32-ru.battleknight.gameforge.com/joust/signUp'
url_joust = 'https://s32-ru.battleknight.gameforge.com/joust'
url_alchemist = 'https://s32-ru.battleknight.gameforge.com/market/merchant/alchemist'

url_name = f"bk\\clan\\BattleKnight_{today.day:02d}_{today.month:02d}.html"
folder_name = f"bk\\statistic\\statistic_{today.day:02d}_{today.month:02d}"
folder_name_loss = f"bk\\statistic_loss\\statistic_loss_{today.day:02d}_{today.month:02d}"

