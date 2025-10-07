import time

import requests
from requests import Timeout, RequestException, Response
from requests.exceptions import ProxyError

from logs.logs import p_log
from module.all_function import get_random_value
from module.data_pars import get_csrf_token, get_title
from module.proxy.proxy_manager import create_proxy_manager, ProxyManager, proxies_validate
from setting import get_cookies, get_header

csrf_token = None
max_csrf_retries = 3
max_retries = 3


class LazyProxyManager:
    _instance = None
    _custom_proxy = None
    _force_enabled = False  # Новый флаг принудительного включения

    def __new__(cls, custom_proxy=None):
        if custom_proxy:
            # Создаем временный менеджер с индивидуальным прокси
            return cls.create_custom_manager(custom_proxy)

        if cls._force_enabled and cls._instance is None:
            cls.enable(force=True)  # Активируем если включен принудительный режим

        if cls._instance is None:
            cls._instance = create_proxy_manager() or None
        return cls._instance

    @classmethod
    def enable(cls, force=True, custom_proxies=None):
        """
        Глобально активирует прокси-менеджер
        :param force: bool - активировать/деактивировать
        :param custom_proxies: list - кастомный список прокси (опционально)
        """
        cls._force_enabled = force
        if force and cls._instance is None:
            if custom_proxies:
                # Используем кастомные прокси если переданы
                cls._instance = ProxyManager(proxies=custom_proxies)
            else:
                # Иначе создаем стандартный менеджер
                cls._instance = create_proxy_manager(read_conf=False)

    @classmethod
    def create_custom_manager(cls, proxy):
        """Создает временный менеджер с одним указанным прокси"""
        validated = proxies_validate(proxy)
        if not validated:
            raise ValueError(f"Неверный формат прокси: {proxy}")
        return ProxyManager(proxies=[proxy])

    @classmethod
    def reset(cls):
        """Сбрасывает текущий экземпляр менеджера"""
        cls._instance = None
        cls._force_enabled = False


def validate_status(response):
    if response.status_code >= 400:
        raise RequestException(f"HTTP Error {response.status_code}: {response.reason}")
    title = get_title(response)
    if title and "error" in title.lower():
        raise RequestException(f"Страница 404: {title}")


def make_http_request(request_func, url, timeout=10, proxy_manager=None, **kwargs):
    """
    Универсальная функция для выполнения HTTP запросов с обработкой ошибок

    Args:
        request_func: функция requests.get или requests.post
        url: URL для запроса
        timeout: таймаут запроса
        proxy_manager: менеджер прокси
        **kwargs: дополнительные параметры для запроса
    """
    global csrf_token
    csrf_retries = 0
    request_retries = 0

    # Извлекаем параметры, которые не нужны для requests
    csrf_enabled = kwargs.pop('csrf', True)  # Удаляем csrf из kwargs

    if isinstance(proxy_manager, str):
        proxy_manager = LazyProxyManager(custom_proxy=proxy_manager)
    elif proxy_manager is None:
        proxy_manager = LazyProxyManager()

    while True:
        try:
            # Установка прокси
            proxies = None
            if proxy_manager:
                current_proxy = proxy_manager.get_current_proxy()
                kwargs['proxies'] = {"http": current_proxy,
                                     "https": current_proxy}
                proxies = kwargs.get('proxies').get('http')

            # Выполнение запроса
            response = request_func(url, timeout=timeout, **kwargs)
            validate_status(response)

            # Логирование
            method = "POST" if request_func == requests.post else "GET"
            p_log(f"{method} {response.status_code}: {url} | proxy:{proxies}", level='debug')

            # CSRF-логика (только для GET запросов)
            if request_func == requests.get and csrf_enabled:
                token = get_csrf_token(response)
                if token and csrf_token != token:
                    p_log(f'CSRF token обновлен (попытка {csrf_retries + 1}/{max_csrf_retries})', level='debug')
                    csrf_token = token

                    if csrf_retries < max_csrf_retries:
                        csrf_retries += 1
                        p_log('Повторный запрос из-за обновления CSRF токена', level='debug')
                        continue
                    else:
                        p_log('Достигнут лимит попыток из-за обновления CSRF токена', level='debug')

            return response

        except ProxyError as e:
            request_retries += 1
            p_log(f"ProxyError: {e}", level='debug')
            p_log(f"Повтор через {timeout} сек...", level='debug')

            if request_retries >= max_retries:
                if proxy_manager:
                    old_proxy = proxy_manager.get_current_proxy()
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


def make_request(url,
                 timeout=10,
                 game_sleep=True,
                 browser_cookies=None,
                 http_headers=None,
                 csrf=True,
                 proxy_manage=None,
                 proxies=None) -> Response:
    """GET запрос"""
    if browser_cookies is None:
        browser_cookies = get_cookies()
    if http_headers is None:
        http_headers = get_header()

    response = make_http_request(
        request_func=requests.get,
        url=url,
        timeout=timeout,
        proxy_manager=proxy_manage,
        cookies=browser_cookies,
        headers=http_headers,
        allow_redirects=True,
        proxies=proxies,
        csrf=csrf
    )

    if game_sleep:
        time.sleep(get_random_value(1, 2.5))
    return response


def post_request(url,
                 data=None,
                 timeout=10,
                 csrf=True,
                 browser_cookies=None,
                 http_headers=None,
                 proxies=None,
                 proxy_manage=None) -> Response:
    """POST запрос"""
    if browser_cookies is None:
        browser_cookies = get_cookies()
    if http_headers is None:
        http_headers = get_header()

    # Добавление CSRF токена если нужно
    if csrf:
        data['csrf_token'] = csrf_token

    response = make_http_request(
        request_func=requests.post,
        url=url,
        timeout=timeout,
        proxy_manager=proxy_manage,
        data=data,
        cookies=browser_cookies,
        headers=http_headers,
        allow_redirects=True,
        proxies=proxies,
        csrf=csrf
    )

    return response
