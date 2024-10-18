from datetime import date
import os
import json
from dotenv import load_dotenv

load_dotenv()

today = date.today()
GOLD_DAY = 2000
CURRENT_TAX = 0.6
waiting_time = 600
start_game = "07:00"

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

url = 'https://s32-ru.battleknight.gameforge.com/clan/members'
url_gold = 'https://s32-ru.battleknight.gameforge.com/clan/upgrades'
url_stat = 'https://s32-ru.battleknight.gameforge.com:443/highscore/'
world_url = 'https://s32-ru.battleknight.gameforge.com/world'
map_url = 'https://s32-ru.battleknight.gameforge.com/world/map'

url_name = f"bk\\clan\\BattleKnight_{today.day:02d}_{today.month:02d}.html"
folder_name = f"bk\\statistic\\statistic_{today.day:02d}_{today.month:02d}"
folder_name_loss = f"bk\\statistic_loss\\statistic_loss_{today.day:02d}_{today.month:02d}"
excel_file_path = f"bk\\result_xlsx\\stat_{today.day:02d}_{today.month:02d}.xlsx"
txt_report = f"bk\\report_clan\\report_{today.day:02d}_{today.month:02d}.txt"
filename = 'config.ini'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
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
status_list = ['Ожидание после дуэли', 'Ожидание после миссии', 'Путешествие', 'Работа', 'Рынок']
status_list_eng = ['Ozhidanie posle dueli', 'Ozhidanie posle missii', 'Puteshestvie', 'Rabota', 'Rynok']
mount_list = {'pegas': '16888797', 'bear': '16896645', 'boar': '17561824', 'unicorn': '16459963'}
