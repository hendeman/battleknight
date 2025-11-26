# logging_config.py
import multiprocessing
from typing import Union

from logs.logger_process import logger_process
from logs.logs import setup_logging as setup_main_logging


class LoggingSystemManager:
    def __init__(self, enable_rotation=True, log_file_path: Union[bool, str] = False):
        self.enable_rotation = enable_rotation
        self.log_file_path = log_file_path
        self.queue = None
        self.logging_process = None
        self.translate = None

    def __enter__(self):
        self.queue, self.logging_process, self.translate = self._setup_logging_system()
        return self.queue, self.logging_process, self.translate

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_logging_system()
        return None

    def _setup_logging_system(self):
        from module.all_function import get_config_value  # импорт внутри, чтобы избежать циклических импортов

        self.translate = get_config_value("translate")

        from setting import CONFIG_NAME

        if self.translate:
            self.queue = multiprocessing.Queue()
            self.logging_process = multiprocessing.Process(
                target=logger_process,
                args=(self.queue, self.enable_rotation, CONFIG_NAME, self.log_file_path)
            )
            self.logging_process.start()
            setup_main_logging(queue=self.queue, enable_rotation=self.enable_rotation, log_file_path=self.log_file_path)
        else:
            setup_main_logging(queue=None, enable_rotation=self.enable_rotation, log_file_path=self.log_file_path)

        return self.queue, self.logging_process, self.translate

    def _cleanup_logging_system(self):
        if self.translate:
            self.queue.put(None)
            self.logging_process.join()
