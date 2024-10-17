import logging
import sys

import colorlog
from logging.handlers import TimedRotatingFileHandler, QueueHandler
import os


def p_log(*args, is_error=False, level='info'):
    message = " ".join(map(str, args))
    # Запись в лог без блокировки
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


def setup_logging(queue=None):
    logger = logging.getLogger()

    # Удаление всех существующих обработчиков
    if logger.hasHandlers():
        logger.handlers.clear()

    # Настройка форматтеров
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s %(message)s",
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'white',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )

    file_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S')

    # Настройка хендлеров
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    log_file_path = "logs/app.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    file_handler = TimedRotatingFileHandler(log_file_path, when="midnight", interval=1, backupCount=10)
    file_handler.setFormatter(file_formatter)

    logger.setLevel(logging.DEBUG)

    # Добавляем обработчики только в основном процессе
    if queue is None:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    else:
        # Если есть очередь, добавляем QueueHandler
        handler = QueueHandler(queue)
        logger.addHandler(handler)

    # Отключаем логирование для библиотеки requests
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.error("Необработанное исключение", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_uncaught_exception


if __name__ == "__main__":
    setup_logging()  # Настраиваем логирование
