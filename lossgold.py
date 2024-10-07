import pickle
from time import sleep

import requests
from bs4 import BeautifulSoup

from all_function import save_file
from setting import cookies, headers

dctl = [761889, 67, 368899, 852409, 959449, 468190, 34050, 92009, 468889, 878542, 903247,
        920010, 953530, 961813, 896788, 913574, 889034, 381159, 463396, 864811, 62249, 889783,
        922885, 750945, 947732, 866195, 964539, 964803, 964825, 964835, 964926, 964981, 416140,
        465339, 965059, 965109, 965143, 965180, 965186, 965236, 965250, 965251, 899962, 916533,
        15956, 40637]

dc = {}

# for i in dctl:
#     url = f'https://s4-ru.battleknight.gameforge.com/common/profile/{i}/Scores/Player'
#     resp = requests.get(url, cookies=cookies, headers=headers)
#     sleep(1)
#     soup = BeautifulSoup(resp.text, 'lxml')
#     a = soup.find('table', class_='profileTable').find_all('tr')[4]
#     dc[i] = {"loss": int(a.text.split()[2])}
#     print(f"{i}: {dc[i]}")
#     sleep(1)
# print(f"Записать новые данные в loss.pickle? [y/n]")
# save_file(dc, 'loss.pickle')
# with open('loss.pickle', 'rb') as file1:
#     loaded_dict = pickle.load(file1)
# print(len(loaded_dict))
url = f'https://s4-ru.battleknight.gameforge.com/common/profile/939129/Scores/Player'
resp = requests.get(url, cookies=cookies, headers=headers)
sleep(1)
soup = BeautifulSoup(resp.text, 'lxml')
a = soup.find('h2').text.replace("\n","").strip()
print(a)