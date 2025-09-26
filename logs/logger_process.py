import copy
import logging
import pickle

from logs.logs import setup_logging
from module.all_function import get_config_value
from module.translator.translator import process_text, restore_string_from_asterisks

LANG = get_config_value("translate")
DICTIONARY = f'module/translator/files/dictionary_{LANG}.pickle'
DICTIONARY_NOT_WORLDS = 'module/translator/files/dictionary_not_worlds.pickle'


def logger_process(queue, enable_rotation, log_file_path):
    setup_logging(enable_rotation=enable_rotation, log_file_path=log_file_path)

    # ЗАГРУЖАЕМ буферный словарь для непереведенных слов
    try:
        with open(DICTIONARY_NOT_WORLDS, 'rb') as f:
            buffer_translate = pickle.load(f)
    except (FileNotFoundError, EOFError):
        buffer_translate = {}  # Если файла нет или он пустой

    # ЗАГРУЖАЕМ существующий словарь при запуске
    try:
        with open(DICTIONARY, 'rb') as f:
            loaded_dict = pickle.load(f)
    except (FileNotFoundError, EOFError):
        logging.warning(f"File not found: {DICTIONARY}")
        loaded_dict = {}

    while True:
        record = queue.get()
        if record is None:  # Завершение процесса
            break

        file_record = copy.copy(record)
        if record.levelno == logging.INFO:
            original_message = record.getMessage()
            try:
                modified_text, word_list = process_text(original_message)
                translate_text = loaded_dict.get(modified_text)
                try:
                    restore_string = restore_string_from_asterisks(translate_text, word_list)
                except AttributeError as er:
                    if original_message not in buffer_translate:
                        buffer_translate[original_message] = modified_text
                        with open(DICTIONARY_NOT_WORLDS, 'wb') as f:
                            pickle.dump(buffer_translate, f)
                    restore_string = original_message

            except Exception as e:
                logging.warning(f"Error processing message '{original_message}': {e}")
                restore_string = original_message  # использовать оригинальное сообщение
            record.msg = restore_string

        # 1. Сначала файл (оригинальный текст) - уровень DEBUG
        file_handler = logging.getLogger().handlers[1]
        if file_handler.level <= file_record.levelno:
            file_handler.handle(file_record)

        # 2. Потом консоль (переведенный текст) - уровень INFO
        console_handler = logging.getLogger().handlers[0]
        if console_handler.level <= record.levelno:
            console_handler.handle(record)
