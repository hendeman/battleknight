from datetime import date

today = date.today()
GOLD_DAY = 29461
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

FILE_NAME = "all_dct.pickle"
STAT_FILE_NAME = "stat_dct.pickle"
STAT_FILE_LOSS = 'loss.pickle'

url = 'https://s32-ru.battleknight.gameforge.com/clan/members'
url_gold = 'https://s32-ru.battleknight.gameforge.com/clan/upgrades'
url_stat = 'https://s32-ru.battleknight.gameforge.com:443/highscore/'

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

cookies = {"BattleKnight": "1ac91687b806a88ae7efa37045538b88%23872161",
           "gf-cookie-consent-4449562312": "|7|1",
           "gf-token-production": "8399cb0a-c288-4ab3-8866-becab8084870",
           "gf_pz_token": "7a5e1530-1cf2-4c93-b52e-f9070cef467a",
           "pc_idt": "APOAx-JAuZR3qtYWKY0aLVBRvROKydsq3RfdpRHR8La0hpAWPiJYqTma7sctQW4mRfoJoevmu-MgK1nZLy1M1vaYtNqc41H4QZBTBI0k8MlqwNsvsvwT2iPAcxKWNv9eKtt9CZ0SL5g0BJcjfHul1S9hb4I-YPJVxnjApw"}

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
