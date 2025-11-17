# logging_config.py
import multiprocessing
from typing import Union

from logs.logger_process import logger_process
from logs.logs import setup_logging as setup_main_logging

queue = None


def setup_logging_system(enable_rotation=True, log_file_path: Union[bool, str] = False):
    """
    Настраивает систему логирования в зависимости от настройки translate.
    Возвращает:
        - queue: объект очереди, если используется перевод
        - logging_process: процесс логирования, если используется перевод
        - translate: флаг, используется ли перевод
    """
    from module.all_function import get_config_value  # импорт внутри, чтобы избежать циклических импортов

    translate = get_config_value("translate")
    global queue
    logging_process = None

    from setting import CONFIG_NAME

    if translate:
        queue = multiprocessing.Queue()
        logging_process = multiprocessing.Process(target=logger_process, args=(queue, enable_rotation,
                                                                               CONFIG_NAME, log_file_path))
        logging_process.start()
        setup_main_logging(queue=queue, enable_rotation=enable_rotation, log_file_path=log_file_path)
    else:
        setup_main_logging(queue=None, enable_rotation=enable_rotation, log_file_path=log_file_path)  # без очереди

    return queue, logging_process, translate


def cleanup_logging_system(queue, logging_process, translate):
    """
    Завершает систему логирования, если использовалась очередь.
    """
    if translate:
        queue.put(None)
        logging_process.join()
