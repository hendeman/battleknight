from datetime import date

from env_loader import load_custom_env

today = date.today()

CHRISTMAS_MODE = False

SERVER = 'https://s32-ru.battleknight.gameforge.com'
LANG = 'ru'
NAME = None
GAME_TOKEN = 'ODcyMTYx'
GOLD_DAY = 25090
GOLD_LIMIT = 7000
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
LOG_DIR = 'logs'
DIRECTORY_PICKLES = 'pickles_data/'
EXTENSION_PICKLES = '.pickle'
# Configs files
filename = 'configs/config.ini'
attack_ids_gamers = 'configs/battle.json'
helpers_info = "configs/helper.json"
attack_ids_path = "configs/id_attack.txt"

excel_file_path = f"bk\\statistic\\stat.xlsx"
path_json = f"bk\\statistic\\"
backup_dir = f"bk\\statistic\\backup\\"
statistic_old_dir = f"bk\\statistic\\statistic_old\\"
statistic_new_dir = f"bk\\statistic\\statistic_new\\"
name_file_old = 'data.json'
name_file_new = 'data_new.json'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 '
                  'Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br'
}
csrf_token = '50fe90e9454b748e58b3dd49951dc0d07da3000d426b531a530c1745ef299298'
cookies = load_custom_env()

castles_island = {'VillageFour': 'Джаро', 'FortressTwo': "Сёгур", 'HarbourTwo': "Альван",
                  'TradingPostFour': 'Милей', 'FogIsland': 'Фехан'}
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
url_orden_message = "/ajax/board/sendmessage"
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
    return NAME


def get_filename():
    return filename


def get_cookies():
    return cookies


def reload_cookies(env_file):
    """Перезагружает куки из указанного .env файла"""
    global cookies
    file_name = env_file + '.env'
    cookies = load_custom_env(file_name)
    return cookies


def reload_config(name_config):
    global filename
    filename = name_config + '.ini'
    return filename


def add_server_prefix():
    for var_name in list(globals().keys()):
        if var_name.startswith('url_'):
            globals()[var_name] = SERVER + globals()[var_name]


add_server_prefix()
