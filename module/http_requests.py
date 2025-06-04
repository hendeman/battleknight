import time
from functools import wraps

import requests
from requests import Timeout, RequestException

from logs.logs import p_log
from module.all_function import get_random_value
from module.data_pars import get_csrf_token, get_title
from setting import cookies, headers

csrf_token = None


def validate_status(response):
    if response.status_code >= 400:
        raise RequestException(f"HTTP Error {response.status_code}: {response.reason}")
    title = get_title(response)
    if title and "error" in title.lower():
        raise RequestException(f"Страница 404: {title}")


def request_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        timeout = kwargs.get('timeout', 10)
        while True:
            try:
                response = func(*args, **kwargs)
                # CSRF-логика только для make_request
                if func.__name__ == 'make_request':
                    global csrf_token
                    token = get_csrf_token(response)
                    if token and csrf_token != token:
                        p_log('CSRF token обновлен', level='debug')
                        csrf_token = token
                return response
            except Timeout as e:
                p_log(f"Timeout: {e}", level='debug')
                p_log(f"Повтор через {timeout} сек...", level='debug')
                time.sleep(timeout)
            except RequestException as e:
                p_log(f"Ошибка: {e}", level='debug')
                p_log(f"Повтор через {timeout} сек...", level='debug')
                time.sleep(timeout)

    return wrapper


@request_error_handler
def make_request(url, timeout=10, game_sleep=True):
    response = requests.get(
        url,
        cookies=cookies,
        headers=headers,
        allow_redirects=True,
        timeout=timeout
    )
    p_log(f"GET {response.status_code}: {url}", level='debug')
    validate_status(response)
    if game_sleep:
        time.sleep(get_random_value(1, 2.5))
    return response


@request_error_handler
def post_request(url, data, timeout=10):
    data['csrf_token'] = csrf_token
    response = requests.post(
        url,
        cookies=cookies,
        headers=headers,
        data=data,
        allow_redirects=True,
        timeout=timeout
    )
    p_log(f"POST {response.status_code}: {url}", level='debug')
    validate_status(response)
    return response
