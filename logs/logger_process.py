import copy
import logging
import os
import pickle

from logs.logs import setup_logging
from module.all_function import get_config_value
from module.translator.translator import process_text, restore_string_from_asterisks

DICTIONARY_NOT_WORLDS = 'module/translator/files/dictionary_not_worlds.pickle'


def get_dictionary(name_file):
    try:
        with open(name_file, 'rb') as f:
            dct = pickle.load(f)
    except (FileNotFoundError, EOFError):
        logging.debug(f"File not found: {name_file}")
        dct = {}
    return dct


def translate_is_enabled(value):
    if isinstance(value, str):
        return value.strip().lower() not in ("0", "false", "no", "off", "", "ru")
    return bool(value)


def logger_process(queue, enable_rotation, config_path, log_file_path):
    import setting

    if setting.CONFIG_NAME != config_path:
        setting.reload_config(config_path)

    LANG = get_config_value("translate")
    USE_TRANSLATE = translate_is_enabled(LANG)

    setup_logging(
        enable_rotation=enable_rotation,
        log_file_path=log_file_path
    )

    if USE_TRANSLATE:
        DICTIONARY = f'module/translator/files/dictionary_{LANG}.pickle'

        buffer_translate = get_dictionary(DICTIONARY_NOT_WORLDS)
        loaded_dict = get_dictionary(DICTIONARY)

        try:
            last_mtime = int(os.path.getmtime(DICTIONARY))
        except FileNotFoundError:
            last_mtime = None
    else:
        DICTIONARY = None
        buffer_translate = {}
        loaded_dict = {}
        last_mtime = None

    while True:
        record = queue.get()

        if record is None:
            break

        file_record = copy.copy(record)

        if USE_TRANSLATE and record.levelno == logging.INFO:
            original_message = record.getMessage()

            try:
                try:
                    current_mtime = int(os.path.getmtime(DICTIONARY))
                except FileNotFoundError:
                    logging.warning(f"File not found: {DICTIONARY}")
                    current_mtime = None

                if last_mtime != current_mtime:
                    loaded_dict = get_dictionary(DICTIONARY)
                    last_mtime = current_mtime

                modified_text, word_list = process_text(original_message)
                translate_text = loaded_dict.get(modified_text)

                try:
                    restore_string = restore_string_from_asterisks(
                        translate_text,
                        word_list
                    )
                except AttributeError:
                    if not os.path.exists(DICTIONARY_NOT_WORLDS):
                        buffer_translate = {}

                    if original_message not in buffer_translate:
                        buffer_translate[original_message] = modified_text

                        with open(DICTIONARY_NOT_WORLDS, 'wb') as f:
                            pickle.dump(buffer_translate, f)

                    restore_string = original_message

            except Exception as e:
                logging.warning(
                    f"Error processing message '{original_message}': {e}"
                )
                restore_string = original_message

            record.msg = restore_string

        root_logger = logging.getLogger()

        file_handler = None
        console_handler = None

        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
            elif isinstance(handler, logging.StreamHandler):
                console_handler = handler

        if file_handler and file_handler.level <= file_record.levelno:
            file_handler.handle(file_record)

        if console_handler and console_handler.level <= record.levelno:
            console_handler.handle(record)