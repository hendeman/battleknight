from datetime import date
from pathlib import Path

from env_loader import load_custom_env

today = date.today()

SERVER = 'https://s32-ru.battleknight.gameforge.com'
NAME = None
ENV_PATH = 'configs'
ENV_NAME = ''
CURRENT_TAX = 0.6
waiting_time = 600
start_game = "09:00"

BAG_CONFIG = {
    'companion': 6,
    'horse': (5, 7)
}

ALL_BAG_NUMS = {6, 5, 7}

NAME_HELPERS = {
    "companion": {'item_name': "itemCompanion", 'type_helper_names': 'компаньон'},
    "horse": {'item_name': "itemHorse", 'type_helper_names': 'наездник'}
}
ATTRIBUTES = ("str", "dex", "end", "luck", "weapon", "defense")
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
STAT_FILE_NAME = "pickles_data/stat/stat_dct.pickle"
STAT_FILE_LOSS = 'pickles_data/loss/loss.pickle'
GOLD_GAMER = 'pickles_data/gamer_gold.pickle'
NICKS_GAMER = 'pickles_data/nicks.pickle'
SAVE_CASTLE = 'pickles_data/save_castle.pickle'
LOG_DIR = 'logs'
LOG_DIR_NAME = 'app'
CONFIG_DIR = 'configs'
CONFIG_NAME = 'config'
LOG_ERROR_HTML = 'logs/error_html'
DIRECTORY_PICKLES = 'pickles_data/'
EXTENSION_PICKLES = '.pickle'
# Configs files
filename = 'configs/config.ini'
attack_ids_gamers = 'configs/battle.json'
helpers_info = "configs/helper.json"
halloween_info = "configs/halloween.json"
attack_ids_path = "configs/id_attack.txt"

excel_file_path = f"bk\\statistic\\stat.xlsx"
path_json = f"bk\\statistic\\"
backup_dir = f"bk\\statistic\\backup\\"
statistic_old_dir = f"bk\\statistic\\statistic_old\\"
statistic_new_dir = f"bk\\statistic\\statistic_new\\"
name_file_old = 'data.json'
name_file_new = 'data_new.json'

cookies, header = load_custom_env()

header_post = {'Sec-fetch-dest': 'empty', 'Sec-fetch-mode': 'cors'}
header_get = {'Sec-fetch-dest': 'document', 'Sec-fetch-mode': 'navigate',
              'Sec-fetch-user': '?1', 'Upgrade-insecure-requests': '1'}

csrf_token = '50fe90e9454b748e58b3dd49951dc0d07da3000d426b531a530c1745ef299298'

grand_region = {'HarbourThree': "Sedwich", 'TradingPostOne': "Grand", 'VillageOne': "Terent"}
brent_region = {'TradingPostThree': "Brent", 'FortressOne': "Tulgar", 'VillageThree': "Rumstill", 'HarbourOne': "Vale"}
alcran_region = {'CityOne': "Alcran", 'CoastalFortressTwo': "Gastein", 'GhostTown': "Talfour"}
hatwig_region = {'VillageTwo': "Hatwig", 'TradingPostTwo': "Talmet"}
endaline_region = {'CapitalCity': "Endaline", 'CoastalFortressOne': "Asgal"}

castles_continent = {**grand_region, **brent_region, **alcran_region, **hatwig_region, **endaline_region}
castles_island = {'VillageFour': 'Djaro', 'FortressTwo': 'Segur', 'HarbourTwo': 'Alvan',
                  'TradingPostFour': 'Miley', 'FogIsland': 'Fehan'}
castles_all = {**castles_continent, **castles_island}

auction_castles = ('HarbourThree', 'TradingPostOne', 'CapitalCity', 'TradingPostTwo',
                   'HarbourOne', 'TradingPostThree', 'VillageThree', 'CityOne',
                   'HarbourTwo', 'TradingPostFour')
castles_symbol = {'v1': 'VillageOne', 'tp1': 'TradingPostOne', 'h3': 'HarbourThree', 'hs': 'CapitalCity',
                  'cf1': 'CoastalFortressOne', 'cf2': 'CoastalFortressTwo', 'c1': 'CityOne', 'v2': 'VillageTwo',
                  'tp2': 'TradingPostTwo', 'h1': 'HarbourOne', 'h2': 'HarbourTwo', 'tp4': 'TradingPostFour',
                  'v4': 'VillageFour', 'f2': 'FortressTwo', 'tp3': 'TradingPostThree', 'v3': 'VillageThree',
                  'f1': 'FortressOne', 'gt': 'GhostTown'}
# status_list = ['Ожидание после дуэли', 'Ожидание после миссии', 'Путешествие', 'Работа', 'Рынок']
joust_status = ('Регистрация',)
work_status = ('Работа',)
type_helper_name = ('наездник', 'компаньон')
start_time = ['09:00', '15:20', '22:50']
potion_name = ['itemPotionRed50', 'itemPotionRed100', 'itemPotionRed200', 'itemPotionBlue300', 'itemPotionBlue500',
               'itemPotionYellowFull', 'itemPotionKarmaSwitch']
potion_name_buy = ['itemPotionRed50', 'itemPotionRed100', 'itemPotionRed200']
event_healer_potions = {1: {'name': "Зелье дружбы", 'price': 5000},
                        2: {'name': "Зелье перспективы", 'price': 2000},
                        3: {'name': "Зелье восприятия", 'price': 1500},
                        4: {'name': "Зелье процветания", 'price': 7000},
                        5: {'name': "Зелье мудрости", 'price': 800},
                        6: {'name': "Зелье природы", 'price': 5000},
                        7: {'name': "Зелье власти", 'price': 5000}}

karma = {'good': {'holy': {'id_karma': 2, 'point': 50, 'name': 'Святая сила'},
                  'ancestors': {'id_karma': 10, 'point': 50, 'name': 'Защита предков'},
                  'regeneration': {'id_karma': 11, 'point': 75, 'name': 'Регенерация'},
                  'angel': {'id_karma': 9, 'point': 150, 'name': 'Крылья ангела'},
                  'shield': {'id_karma': 8, 'point': 200, 'name': 'Мистический щит'},
                  'stronghold': {'id_karma': 12, 'point': 225, 'name': 'Мистическая цитадель'}},
         'evil': {'unholy': {'id_karma': 1, 'point': 50, 'name': 'Темная сила'},
                  'perdition': {'id_karma': 4, 'point': 50, 'name': 'Проклятье'},
                  'shadow': {'id_karma': 7, 'point': 75, 'name': 'Тень тьмы'},
                  'scream': {'id_karma': 3, 'point': 150, 'name': 'Крик смерти'},
                  'acid': {'id_karma': 5, 'point': 150, 'name': 'Удар кислотой'},
                  'thorns': {'id_karma': 6, 'point': 200, 'name': 'Броня с шипами'}}}

# _____________________________________ Игровые префиксы _____________________________________________
url_members = '/clan/members'
url_gold = '/clan/upgrades'
url_stat = '/highscore/'
url_karma = '/user/karma/'
url_world = '/world'
url_map = '/world/map'
url_compare = '/duel/compare/?enemyID='
url_duel_name = "/duel/duel/?enemyID="
url_group = '/groupmission/group/'
url_group_members = '/groupmission/groupMembers'
url_group_pas = '/groupmission/dice'
url_group_delete = '/groupmission/deleteGroup'
url_greate_group = '/groupmission/foundGroup/'
url_refresh_groups = '/groupmission/refreshGroups'
url_join_group = '/groupmission/joinGroup/?groupID='
url_orden_message = "/ajax/board/sendmessage"
url_private_message = "/ajax/mail/sendMail"
url_ordermail = "/mail/ordermail"
url_error = "/common/error"
url_start_travel = '/world/startTravel'
url_mission = '/world/location'
url_travel = '/world/travel'
url_market = '/market/merchant/artefacts'
url_loot = '/user/loot/'
url_work = '/market/work'
url_treasury = '/treasury'
url_deposit = '/treasury/deposit'
url_user = '/user/'
url_point = '/user/getPotionBar'
url_auctioneer = '/market/auctioneer'
url_payout = '/treasury/payout'
url_duel = '/duel/'
url_joust_sign = '/joust/signUp'
url_joust = '/joust'
url_alchemist = '/market/merchant/alchemist'
url_healer = '/zanyhealer/buyAndUsePotion/'
url_zany_healer = '/zanyhealer/'
url_raise_attr = '/ajax/ajax/raiseAttribute/?attribute='

months = {
    1: "январь", 2: "февраль", 3: "март",
    4: "апрель", 5: "май", 6: "июнь",
    7: "июль", 8: "август", 9: "сентябрь",
    10: "октябрь", 11: "ноябрь", 12: "декабрь"
}

clan_html_file = (f"bk\\clan\\{today.year}\\{months.get(today.month)}"
                  f"\\BattleKnight_{today.day:02d}_{today.month:02d}.html")
folder_name = (f"bk\\statistic\\{today.year}\\{months.get(today.month)}"
               f"\\statistic_{today.day:02d}_{today.month:02d}")
folder_name_loss = (f"bk\\statistic_loss\\{today.year}\\{months.get(today.month)}"
                    f"\\statistic_loss_{today.day:02d}_{today.month:02d}")


def get_name():
    if NAME is None:
        raise AttributeError('Доступ запрещен')
    return NAME


def get_filename():
    return filename


def get_cookies():
    return cookies


def get_header():
    headers = {
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Sec-ch-ua-mobile': "?0",
        'Sec-ch-ua-platform': "Windows",
        'Sec-fetch-site': 'same-origin',
        'Connection': 'keep-alive'
    }
    return dict(**headers, **header)


def reload_cookies(env_file):
    """Перезагружает куки из указанного .env файла"""
    global cookies, header, ENV_NAME
    file_name = Path(ENV_PATH) / f"{env_file}.env"
    ENV_NAME = env_file
    cookies, header = load_custom_env(file_name)
    return cookies, header


def get_env_path():
    return ENV_NAME


def reload_config(name_config):  # name_config = robusta
    global filename, LOG_DIR_NAME, CONFIG_NAME
    filename = Path(CONFIG_DIR) / f"{name_config}.ini"
    LOG_DIR_NAME = name_config
    CONFIG_NAME = name_config
    return filename


def add_server_prefix():
    for var_name in list(globals().keys()):
        if var_name.startswith('url_'):
            globals()[var_name] = SERVER + globals()[var_name]


add_server_prefix()
