import pickle
import re
from pathlib import Path


LANG = 'eng'

DIRECTORIES = ["../../dragon.py", "../../click.py", "../../game_play.py", "../../keys.py", "../../main.py",
               "../../online.py", "../../stats_server.py", "../../war.py", "../../robusta.py", ".."]
FILE_NAME_RU = 'files/ru_phrases.txt'
FILE_NAME_LANG = f'files/{LANG}_phrases.txt'
DICTIONARY = f'files/dictionary_{LANG}.pickle'
DICTIONARY_NOT_WORLDS = 'files/dictionary_not_worlds.pickle'


def save_txt(filename, messages):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            for message in messages:
                file.write(message + '\n')
        print(f"Сообщения успешно сохранены в файл: {filename}")
        print(f"Сохранено сообщений: {len(messages)}")
    except Exception as e:
        print(f"Ошибка при сохранении в файл {filename}: {e}")


def read_txt(filename):
    read_lst = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as file:
            read_lst = [line.strip() for line in file]
    except Exception as e:
        print(f"Файл не найден {filename}: {e}")
    return read_lst


def process_text(text):
    # Паттерн: только парные скобки, без вложенности
    brackets_pattern = r'(\((?:[^\(\)]*)\))|(\[(?:[^\[\]]*)\])|(\{(?:[^{}]*)\})'
    cyrillic_word_with_hyphen = r'\b[а-яёА-ЯЁ]+(?:-[а-яёА-ЯЁ]+)*\b'
    latin_or_digit_word = r'\S*[a-zA-Z0-9]\S*'

    matches = []

    for match in re.finditer(brackets_pattern, text):
        matches.append((match.start(), match.end(), match.group()))

    for match in re.finditer(latin_or_digit_word, text):
        word = match.group()
        if not re.fullmatch(cyrillic_word_with_hyphen, word):
            matches.append((match.start(), match.end(), word))

    matches.sort(key=lambda x: x[0])

    # Убираем пересекающиеся
    filtered_matches = []
    last_end = -1
    for start, end, group in matches:
        if start >= last_end:
            filtered_matches.append((start, end, group))
            last_end = end

    ordered_replaced = [item[2] for item in filtered_matches]

    # Заменяем
    result = text
    for start, end, group in reversed(filtered_matches):
        result = result[:start] + '*' + result[end:]

    return result, ordered_replaced


def restore_string_from_asterisks(modified_text, word_list):
    """
    Восстанавливает исходную строку, заменяя * на слова из списка

    Args:
        modified_text: строка с звездочками ("Ожидание * часов...")
        word_list: список слов для замены (['45', 'process_name'])

    Returns:
        Восстановленная строка или исходная, если количество * не совпадает
    """
    # Подсчитываем количество звездочек в строке
    asterisk_count = modified_text.count('*')

    # Проверяем соответствие количества
    if asterisk_count != len(word_list):
        return modified_text  # или можно вернуть исходную строку

    # Восстанавливаем строку
    res = modified_text
    for word in word_list:
        # Заменяем первую найденную звездочку
        res = res.replace('*', word, 1)

    return res


def extract_cyrillic_messages_from_files(file_paths):
    """
    Извлекает кириллические сообщения из строк p_log в .py файлах,
    заменяя содержимое в {} на * и не-кириллические слова на *
    """
    unique_messages = set()

    # Преобразуем входные данные в список Path объектов
    paths_to_process = []

    if isinstance(file_paths, str):
        path_obj = Path(file_paths)
        if path_obj.is_dir():
            paths_to_process = list(path_obj.rglob("*.py"))
        elif path_obj.is_file() and path_obj.suffix == '.py':
            paths_to_process = [path_obj]
        else:
            print(f"Указанный путь не существует или не является .py файлом: {file_paths}")
            return []

    elif isinstance(file_paths, Path):
        if file_paths.is_dir():
            paths_to_process = list(file_paths.rglob("*.py"))
        elif file_paths.is_file() and file_paths.suffix == '.py':
            paths_to_process = [file_paths]
        else:
            print(f"Указанный путь не существует или не является .py файлом: {file_paths}")
            return []

    elif isinstance(file_paths, list):
        for item in file_paths:
            if isinstance(item, (str, Path)):
                path_obj = Path(item) if isinstance(item, str) else item
                if path_obj.is_dir():
                    paths_to_process.extend(list(path_obj.rglob("*.py")))
                elif path_obj.is_file() and path_obj.suffix == '.py':
                    paths_to_process.append(path_obj)
                else:
                    print(f"Пропускаем несуществующий путь: {item}")

    # Регулярное выражение для поиска строк p_log с кириллицей
    p_log_pattern = re.compile(r'p_log\(f?"([^"]*[А-Яа-яЁё][^"]*)"\)')

    for file_path in paths_to_process:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    # Проверяем, что строка начинается с p_log и заканчивается на скобку
                    if line.startswith('p_log(') and line.endswith(')'):
                        # Ищем кириллические сообщения
                        match = p_log_pattern.search(line)
                        if match:
                            message = match.group(1)

                            # 1. Сначала обрабатываем вложенные {} - заменяем все содержимое {} на *
                            # Используем рекурсивный подход для вложенных скобок
                            stack = []
                            result_chars = []

                            for char in message:
                                if char == '{':
                                    stack.append(char)
                                    if len(stack) == 1:  # Начинается новая группа {}
                                        result_chars.append('*')
                                elif char == '}':
                                    if stack:
                                        stack.pop()
                                else:
                                    if not stack:  # Добавляем только если не внутри {}
                                        result_chars.append(char)

                            message = ''.join(result_chars)

                            # 2. Затем заменяем не-кириллические слова на *
                            message, _ = process_text(message)

                            unique_messages.add(message)

        except UnicodeDecodeError:
            try:
                # Пробуем альтернативную кодировку
                with open(file_path, 'r', encoding='cp1251') as file:
                    for line in file:
                        line = line.strip()
                        if line.startswith('p_log(') and line.endswith(')'):
                            match = p_log_pattern.search(line)
                            if match:
                                message = match.group(1)

                                # Обрабатываем вложенные {}
                                stack = []
                                result_chars = []

                                for char in message:
                                    if char == '{':
                                        stack.append(char)
                                        if len(stack) == 1:
                                            result_chars.append('*')
                                    elif char == '}':
                                        if stack:
                                            stack.pop()
                                    else:
                                        if not stack:
                                            result_chars.append(char)

                                message = ''.join(result_chars)
                                message, _ = process_text(message)

                                unique_messages.add(message)
            except Exception as e:
                print(f"Ошибка кодировки в файле: {file_path}: {e}")

        except Exception as e:
            print(f"Ошибка при обработке файла {file_path}: {e}")

    return sorted(list(unique_messages))


def create_dictionary(original_path_txt, translation_path_txt):
    dictionary = {}
    original_lst = read_txt(original_path_txt)
    translation_lst = read_txt(translation_path_txt)
    if len(original_lst) == len(translation_lst):
        for original, translation in zip(original_lst, translation_lst):
            dictionary[original] = translation
        with open(DICTIONARY, 'wb') as f:
            pickle.dump(dictionary, f)
            print(f"Данные успешно обновлены в файл.")
    else:
        print(f"Не совпадают размерности файлов {original_path_txt}->{len(original_path_txt)} и "
              f"{translation_path_txt}->{len(translation_path_txt)}")


def read_dictionary(file=DICTIONARY):
    with open(file, 'rb') as f:
        loaded_dict = pickle.load(f)
    return loaded_dict


def add_read_dictionary(original_text, translation_text):
    loaded_dict = read_dictionary()
    loaded_dict[original_text] = translation_text
    with open(DICTIONARY, 'wb') as f:
        pickle.dump(loaded_dict, f)
        print(f"Данные успешно обновлены в файл.")


if __name__ == "__main__":
    # result = extract_cyrillic_messages_from_files(DIRECTORIES)
    # print(len(result))
    # for i in result:
    #     print(i)
    # save_txt(FILE_NAME, result)
    # create_dictionary(FILE_NAME_RU, FILE_NAME_LANG)
    # read_dictionary()
    # add_read_dictionary('компаньон Черепашка надет', 'Turtle companion is on')
    # for mes, val in read_dictionary(file=DICTIONARY_NOT_WORLDS).items():
    #     print(f"{mes}: {val}")
    print(process_text("Будет куплено кольцо с id=900959106"))
