import json
import re
import random

from logs.logs import p_log
from module.all_function import get_config_value
from module.war.settings import castles


def extract_script_content(html_content):
    """
        scripts содержит список всех <script> тегов
        last_script выбирает <script>, который содержит 'var castle'
        function_pattern выбирает всю информацию до слова function
    """
    script_pattern = r'<script.*?>(.*?)<\/script>'
    scripts = re.findall(script_pattern, html_content, re.DOTALL)

    if scripts:
        last_script = next((script for script in scripts if script and 'var castle' in script), None)
        function_pattern = r'(.*?)\bfunction\b'
        match = re.search(function_pattern, last_script, re.DOTALL)

        if match:
            return match.group(1)

    return ""


def decode_unicode(string, flag='title'):
    if flag == 'title':
        string = string.replace(r'\/', '/').replace(r'\\', '\\')
        return string.encode('utf-8').decode('unicode_escape')
    else:
        string = string.replace(r'\/', '/').replace(r'\\', '\\')
        clean_text = extract_inner_text(string)
        return clean_text.encode('utf-8').decode('unicode_escape')


def extract_inner_text(text):
    # Находим все текстовые блоки внутри HTML-тегов
    inner_texts = re.findall(r'>(.*?)<', text)  # Находит текст между закрывающим и открывающим тегами
    # Объединяем и очищаем текст
    return ' '.join(inner_texts).strip()


def remove_html_tags(text):
    clean = re.compile('<.*?>')  # Шаблон для поиска HTML-тегов
    return re.sub(clean, '', text)  # Удаляет все теги


def main_pars_clanwar(soup, save=True):
    # # Открываем HTML-файл и читаем его содержимое
    # with open('clanwar_answer_trade_name1_retry.html', 'r', encoding='utf-8') as file:
    #     html_content = file.read()

    script_content = extract_script_content(soup)
    attack_castle_num = int(get_config_value(key='attack_castle'))
    try:
        if script_content:
            castle_pattern = r'castle\s*=\s*document\.id\("(\w+)"\);'
            details_pattern = r'castle\.store\(\s*\'castleDetails\',\s*(\{.*?\})\s*\);'
            tip_title_pattern = r'castle\.store\(\s*\'tip:title\',\s*"(.*?)"\s*\);'
            tip_text_pattern = r'castle\.store\(\s*\'tip:text\',\s*"(.*?)"\s*\);'

            matches = re.findall(castle_pattern, script_content)
            castles_dict = {}
            for match in matches:
                # Ищем данные для текущего идентификатора замка
                detail_match = re.search(details_pattern, script_content)
                if detail_match:
                    castle_data = eval(detail_match.group(1))

                    # Создаём уникальный идентификатор на основе данных замка
                    # castle_id = castle_data["castleID"]

                    # Удаляем обработанные данные о замке из script_content
                    script_content = script_content.replace(detail_match.group(0), '', 1)

                    # Ищем заголовок и текст для текущего замка
                    title_match = re.search(tip_title_pattern, script_content)
                    text_match = re.search(tip_text_pattern, script_content)

                    # Если не нашли, выходим из цикла
                    if not title_match or not text_match:
                        break

                    # tip_title = decode_unicode(title_match.group(1), flag='title') if title_match else ""
                    tip_text = decode_unicode(text_match.group(1), flag='text') if text_match else ""

                    castle_info = {
                        "castleID": castle_data["castleID"],
                        "clanName": castle_data["clanName"],
                        "clanTag": castle_data["clanTag"],
                        "clanID": castle_data["clanID"],
                        "castleSize": castle_data["castleSize"],
                        "castleName": castle_data["castleName"],
                        "tip": tip_text
                    }

                    # Сохраняем в словарь с ключом идентификатора замка
                    castles_dict[match] = castle_info

                    # Удаляем заголовок и текст, чтобы не использовать их снова
                    script_content = script_content.replace(title_match.group(0), '', 1)
                    script_content = script_content.replace(text_match.group(0), '', 1)

            try:
                with open(castles, 'w', encoding="utf-8-sig") as file_gamer:
                    json.dump(castles_dict, file_gamer, ensure_ascii=False, indent=4)
                    p_log(f"Файл {castles} обновлен", level='debug')
            except Exception as er:
                p_log(f"Ошибка записи {castles}: {er}")

            if not save:
                return castles_dict

            # p_log(output, level='debug')
            output_free = [value['castleID'] for key, value in castles_dict.items() if
                           value['clanName'] == 'свободный замок'
                           and not value['tip']]
            p_log(f"Свободные замки {output_free}")

            if attack_castle_num in output_free:
                return attack_castle_num

            output_free_random = random.choice(output_free)
            return output_free_random
        else:
            p_log("Содержимое тега <script> не найдено или не содержит данных до 'function'.")
    except Exception as f:
        p_log(f"Ошибка парсинга карты замков: {f}", is_error=True)
        p_log(f"Будет произведена атака на замок <{attack_castle_num}> из config")
        return attack_castle_num
