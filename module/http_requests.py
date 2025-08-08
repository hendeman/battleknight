import time
from functools import wraps

import requests
from requests import Timeout, RequestException
from requests.exceptions import ProxyError

from logs.logs import p_log
from module.all_function import get_random_value
from module.data_pars import get_csrf_token, get_title
from module.proxy.proxy_manager import create_proxy_manager, ProxyManager, proxies_validate
from setting import cookies, headers

csrf_token = None
max_csrf_retries = 3


class LazyProxyManager:
    _instance = None
    _custom_proxy = None

    def __new__(cls, custom_proxy=None):
        if custom_proxy:
            # Создаем временный менеджер с кастомным прокси
            return cls.create_custom_manager(custom_proxy)

        if cls._instance is None:
            cls._instance = create_proxy_manager() or None
        return cls._instance

    @classmethod
    def create_custom_manager(cls, proxy):
        """Создает временный менеджер с одним указанным прокси"""
        validated = proxies_validate(proxy)
        if not validated:
            raise ValueError(f"Неверный формат прокси: {proxy}")
        return ProxyManager(proxies=[proxy])


def validate_status(response):
    if response.status_code >= 400:
        raise RequestException(f"HTTP Error {response.status_code}: {response.reason}")
    title = get_title(response)
    if title and "error" in title.lower():
        raise RequestException(f"Страница 404: {title}")


def request_error_handler(func):
    @wraps(func)
    def wrapper(url, *args, **kwargs):
        timeout = kwargs.get('timeout', 10)
        csrf = kwargs.get('csrf', False)
        proxies = kwargs.get('proxies', None)
        proxy_manager = kwargs.get('proxy_manage', LazyProxyManager())

        if isinstance(proxy_manager, str):
            proxy_manager = LazyProxyManager(custom_proxy=proxy_manager)

        max_retries = 3
        csrf_retries = 0  # Счетчик попыток из-за CSRF
        request_retries = 0

        while True:
            try:
                if proxy_manager:
                    current_proxy = proxy_manager.get_current_proxy()
                    kwargs['proxies'] = {"http": current_proxy,
                                         "https": current_proxy}
                    proxies = kwargs.get('proxies').get('http')

                response = func(url, *args, **kwargs)
                validate_status(response)

                if func.__name__ == 'make_request':
                    p_log(f"GET {response.status_code}: {url} | proxy:{proxies}", level='debug')
                else:
                    p_log(f"POST {response.status_code}: {url} | proxy:{proxies}", level='debug')

                # CSRF-логика только для make_request
                if func.__name__ == 'make_request' and csrf:
                    global csrf_token
                    token = get_csrf_token(response)

                    if token and csrf_token != token:
                        p_log(f'CSRF token обновлен (попытка {csrf_retries + 1}/{max_csrf_retries})', level='debug')
                        csrf_token = token

                        # Если токен изменился и еще не превышен лимит попыток
                        if csrf_retries < max_csrf_retries:
                            csrf_retries += 1
                            p_log('Повторный запрос из-за обновления CSRF токена', level='debug')
                            continue  # Повторяем цикл с новым токеном
                        else:
                            p_log('Достигнут лимит попыток из-за обновления CSRF токена', level='debug')

                return response
            except ProxyError as e:
                request_retries += 1
                old_proxy = proxy_manager.get_current_proxy()
                p_log(f"ProxyError: {e}", level='debug')
                p_log(f"Повтор через {timeout} сек...", level='debug')

                if request_retries >= max_retries:
                    new_proxy = proxy_manager.get_next_proxy()
                    p_log(f"Превышено количество попыток для прокси {old_proxy}", level='debug')
                    p_log(f"Будет выбран следующий прокси {new_proxy}", level='debug')
                    request_retries = 0

            except Timeout as e:
                p_log(f"Timeout: {e}", level='debug')
                p_log(f"Повтор через {timeout} сек...", level='debug')

            except RequestException as e:
                p_log(f"Ошибка: {e}", level='debug')
                p_log(f"Повтор через {timeout} сек...", level='debug')

            time.sleep(timeout)

    return wrapper


@request_error_handler
def make_request(url,
                 timeout=10,
                 game_sleep=True,
                 browser_cookies=cookies,
                 http_headers=headers,
                 csrf=True,
                 proxy_manage=None,
                 proxies=None):
    response = requests.get(
        url,
        cookies=browser_cookies,
        headers=http_headers,
        allow_redirects=True,
        timeout=timeout,
        proxies=proxies
    )
    if game_sleep:
        time.sleep(get_random_value(1, 2.5))
    return response


@request_error_handler
def post_request(url,
                 data,
                 timeout=10,
                 csrf=True,
                 browser_cookies=cookies,
                 http_headers=headers,
                 proxies=None,
                 proxy_manage=None):
    """ Без csrf_token следующие POST-запросы:
        - создание группы, пас-группы;
        - получение списка баночек getPotionBar"""

    if csrf:
        data['csrf_token'] = csrf_token
    response = requests.post(
        url,
        cookies=browser_cookies,
        headers=http_headers,
        data=data,
        allow_redirects=True,
        timeout=timeout,
        proxies=proxies
    )
    return response
