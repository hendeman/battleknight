import time

import requests
from requests import Timeout, RequestException

from logs.logs import p_log
from setting import cookies, headers


def make_request(url):
    while True:
        try:
            response = requests.get(url, cookies=cookies, headers=headers, allow_redirects=True, timeout=10)
            p_log("GET otvet", response.status_code, level='debug')
            return response

        except Timeout as e:
            p_log("Connection error:", e, level='warning')
            p_log("The waiting time has expired. Check your network connection and server availability.", level='debug')
            p_log("Try again after 10 seconds...", level='debug')
            time.sleep(10)

        except RequestException as e:
            p_log("Connection error:", e, level='warning')
            p_log("Try again after 10 seconds...", level='debug')
            time.sleep(10)  # Подождать некоторое время перед повторной попыткой


def post_request(make_post_url, data):
    while True:
        try:
            response = requests.post(make_post_url, cookies=cookies, headers=headers, data=data,
                                     allow_redirects=True, timeout=10)
            p_log("POST otvet", response.status_code, level='debug')
            return response

        except RequestException as e:
            p_log("Connection error:", e, level='warning')
            p_log("Try again after 5 seconds...", level='warning')
            time.sleep(5)  # Подождать некоторое время перед повторной попыткой