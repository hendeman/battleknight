import logging
import sys

import colorlog
from logging.handlers import TimedRotatingFileHandler
import os
import multiprocessing

# Создание блокировки
log_lock = multiprocessing.Lock()

def p_log(*args, is_error=False, level='info'):
    message = " ".join(map(str, args))
    with log_lock:  # Используем блокировку при записи логов
        if is_error:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Необработанное исключение: " + message, exc_info=(exc_type, exc_value, exc_traceback))
        else:
            if level == 'debug':
                logging.debug(message)
            elif level == 'warning':
                logging.warning(message)
            elif level == 'error':
                logging.error(message)
            else:
                logging.info(message)


def setup_logging():
    # Настройка цветного форматтера для консоли
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s %(message)s",
        datefmt='%H:%M:%S',  # Формат времени без миллисекунд
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'white',  # Сообщения уровня INFO будут белыми
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )

    # Настройка обычного форматтера для файла
    file_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s',
                                       datefmt='%H:%M:%S')  # Убираем миллисекунды

    # Настройка хендлера для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    # Настройка хендлера для ротации файлов
    log_file_path = "logs/app.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)  # Создаем директорию, если она не существует

    file_handler = TimedRotatingFileHandler(log_file_path, when="midnight", interval=1, backupCount=10)
    file_handler.setFormatter(file_formatter)

    # Настройка основного логгера
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Общий уровень логирования

    # Добавляем хендлеры
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Отключаем логирование для библиотеки requests
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # Отключаем логи urllib3

    # Функция-обработчик исключений
    def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Игнорируем прерывание с клавиатуры (Ctrl+C)
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        # Логируем исключение
        logging.error("Необработанное исключение", exc_info=(exc_type, exc_value, exc_traceback))

    # Устанавливаем обработчик для необработанных исключений
    sys.excepthook = handle_uncaught_exception


setup_logging()  # Настраиваем логирование
