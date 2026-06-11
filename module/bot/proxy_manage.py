import os
import logging
import threading
import time
from pathlib import Path
from telebot import apihelper
from module.proxy.proxy_manager import proxies_validate

PROXY_FILE = 'proxy.txt'


class ProxyManager:
    def __init__(self, proxy_file=PROXY_FILE, check_interval=5):
        # Нормализуем путь: преобразуем строку в Path, если нужно
        if isinstance(proxy_file, str):
            self.proxy_file = Path(__file__).parent / proxy_file
        elif isinstance(proxy_file, Path):
            self.proxy_file = proxy_file
        else:
            raise TypeError(f"proxy_file должен быть str или Path, получен {type(proxy_file)}")

        self.check_interval = check_interval
        self.last_mtime = None
        self.running = False
        self.monitor_thread = None
        self.proxy = None

    def load_proxy_from_file(self):
        """Загружает прокси из файла"""
        if not os.path.exists(self.proxy_file):
            return None

        try:
            with open(self.proxy_file, 'r', encoding="utf-8-sig") as f:
                proxy_line = f.read().strip()
                if not proxy_line:
                    self.proxy = None
                    return None

                if proxy_line and not proxy_line.startswith('#') and proxies_validate(proxy_line):
                    if not proxy_line.startswith('http://') and not proxy_line.startswith('https://'):
                        proxy_line = 'http://' + proxy_line
                    self.proxy = {'https': proxy_line}
                    return {'https': proxy_line}

        except Exception as e:
            logging.error(f"Ошибка чтения файла прокси: {e}")
        return None

    def update_proxy_if_changed(self):
        """Обновляет прокси если файл изменился"""
        try:
            if os.path.exists(self.proxy_file):
                current_mtime = os.path.getmtime(self.proxy_file)

                if self.last_mtime is None or current_mtime != self.last_mtime:
                    new_proxy = self.load_proxy_from_file()
                    if new_proxy:
                        # ← ВОТ ЗДЕСЬ МЕНЯЕТСЯ ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ
                        apihelper.proxy = new_proxy
                        self.last_mtime = current_mtime
                        logging.info(f"✅ Прокси обновлен: {new_proxy['https']}")
                        return True
                    else:
                        logging.warning("Файл прокси изменился")
                        if not self.proxy:
                            logging.info("Работаем без прокси")
                        else:
                            logging.info("Невалидный прокси. Будет использован предыдущий")
                        self.last_mtime = current_mtime
                        apihelper.proxy = self.proxy
            else:
                if self.last_mtime is not None:
                    logging.warning(f"Файл прокси {self.proxy_file} не найден, работаем без прокси")
                    apihelper.proxy = None  # ← И ЗДЕСЬ ТОЖЕ
                    self.last_mtime = None
        except Exception as e:
            logging.error(f"Ошибка при проверке прокси: {e}")

        return False

    def _monitor(self):
        """Внутренний метод мониторинга"""
        logging.info(f"🔄 Запущен мониторинг прокси (файл: {self.proxy_file}, интервал: {self.check_interval}с)")
        while self.running:
            try:
                self.update_proxy_if_changed()
            except Exception as e:
                logging.error(f"Ошибка в мониторе прокси: {e}")
            time.sleep(self.check_interval)

    def start(self):
        """Запускает мониторинг прокси в фоновом потоке"""
        if self.running:
            logging.warning("Мониторинг прокси уже запущен")
            return False

        # Загружаем начальный прокси
        initial_proxy = self.load_proxy_from_file()
        if initial_proxy:
            apihelper.proxy = initial_proxy  # ← УСТАНАВЛИВАЕМ НАЧАЛЬНЫЙ ПРОКСИ
            logging.info(f"Загружен начальный прокси: {initial_proxy['https']}")
            if os.path.exists(self.proxy_file):
                self.last_mtime = os.path.getmtime(self.proxy_file)
        else:
            logging.info("Работа без прокси (файл proxy.txt не найден или пуст)")

        # Запускаем поток мониторинга
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()
        return True

    def stop(self):
        """Останавливает мониторинг прокси"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logging.info("Мониторинг прокси остановлен")

    def reload_now(self):
        """Принудительная перезагрузка прокси"""
        logging.info("Принудительная перезагрузка прокси")
        return self.update_proxy_if_changed()

    @staticmethod
    def get_current_proxy():
        """Возвращает текущий используемый прокси"""
        return apihelper.proxy


# Создаем глобальный экземпляр
default_proxy_manager = ProxyManager()


def init_proxy_manager(proxy_file=PROXY_FILE, check_interval=5, auto_start=True):
    """Удобная функция для инициализации менеджера прокси"""
    manager = ProxyManager(proxy_file, check_interval)
    if auto_start:
        manager.start()
    return manager
