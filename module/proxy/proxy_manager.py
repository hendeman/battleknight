import configparser
import time

from logs.logs import p_log
from module.proxy.proxy_checker import proxy_checker
from setting import filename


def proxies_validate(proxy: str):
    num = proxy.replace(":", "").replace(".", "").strip()
    length = len(proxy.split(":"))
    return num.isdigit() and length == 2 and len(proxy.split(".")) == 4


def create_proxy_manager():
    config = configparser.ConfigParser()
    config.read(filename)
    if not config.getboolean('proxy', 'enabled', fallback=False):
        return None

    proxy_list = [
        p.strip()
        for p in config.get('proxy', 'proxy_list', fallback='').split(',')
        if proxies_validate(p)
    ]

    return ProxyManager(
        proxies=proxy_list,
        update_callback=proxy_checker
    )


class ProxyManager:
    def __init__(self, proxies=None, update_callback=None):
        self.proxies = proxies or []
        self.update_callback = update_callback  # Функция для обновления списка
        self._current_proxy = None  # Текущий рабочий прокси
        self._iterator = self._create_iterator()

    def _create_iterator(self):
        """Создает итератор с обработкой конца списка"""
        index = 0
        while True:
            if index >= len(self.proxies):
                if self.update_callback:
                    new_proxies = self.update_callback()  # Вызываем обновление
                    if new_proxies:
                        self.proxies = new_proxies
                        index = 0  # Сбрасываем индекс
                        continue
                    p_log("update_callback вернул пустой список", level='debug')
                    wait_update_proxy = 60
                    p_log(f"Пауза {wait_update_proxy} секунд перед следующей проверкой", level='debug')
                    time.sleep(wait_update_proxy)
                    if not self.proxies:
                        continue
                index = 0  # Начинаем заново даже без обновления

            yield self.proxies[index]
            index += 1

    def get_current_proxy(self):
        """Возвращает текущий рабочий прокси или берет новый если его нет"""
        if self._current_proxy is None:
            self._current_proxy = next(self._iterator)
        return self._current_proxy

    def get_next_proxy(self):
        """Берет следующий прокси и делает его текущим"""
        self._current_proxy = next(self._iterator)
        return self._current_proxy

    def reset_current_proxy(self):
        """Сбрасывает текущий прокси, чтобы взять новый при следующем запросе"""
        self._current_proxy = None
