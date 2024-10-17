import logging
from .logs import setup_logging


def logger_process(queue):
    setup_logging()  # Настройка логирования в отдельном процессе

    while True:
        record = queue.get()
        if record is None:  # Завершение процесса
            break
        logging.getLogger().handle(record)  # Обработка записи
