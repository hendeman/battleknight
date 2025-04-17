import time

import requests
from requests import Timeout, RequestException

from logs.logs import p_log
from module.all_function import get_random_value
from module.data_pars import get_csrf_token
from setting import cookies, headers

csrf_token = None


def make_request(url, timeout=10, game_sleep=True):
    global csrf_token
    while True:
        try:
            response = requests.get(url, cookies=cookies, headers=headers, allow_redirects=True, timeout=timeout)
            p_log("GET ответ:", response.status_code, "URL:", url, level='debug')
            if game_sleep:
                time.sleep(get_random_value(1, 2.5))
            token = get_csrf_token(response)
            if token:
                if csrf_token != token:
                    p_log(f'csrf_token изменился')
                csrf_token = token
            return response

        except Timeout as e:
            p_log("Connection error:", e, level='debug')
            p_log("The waiting time has expired. Check your network connection and server availability.", level='debug')
            p_log("Try again after 10 seconds...", level='debug')
            time.sleep(timeout)

        except RequestException as e:
            p_log("Connection error:", e, level='debug')
            p_log("Try again after 10 seconds...", level='debug')
            time.sleep(timeout)  # Подождать некоторое время перед повторной попыткой


def post_request(make_post_url, data, timeout=10):
    data['csrf_token'] = csrf_token
    while True:
        try:
            response = requests.post(make_post_url, cookies=cookies, headers=headers, data=data,
                                     allow_redirects=True, timeout=timeout)
            p_log("POST ответ:", response.status_code, "URL:", make_post_url, level='debug')
            return response

        except RequestException as e:
            p_log("Connection error:", e, level='debug')
            p_log("Try again after 5 seconds...", level='debug')
            time.sleep(timeout - 1)  # Подождать некоторое время перед повторной попыткой