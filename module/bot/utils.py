import os


def load_allowed_users(file_path, chat_id):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            users = {int(line.strip()) for line in f}
        users.add(chat_id)
        return users
    return {chat_id}


def save_allowed_users(file_path, allowed_users):
    with open(file_path, 'w') as f:
        for user_id in allowed_users:
            f.write(f"{user_id}\n")


def read_last_lines(file, lines=15):
    with open(file, 'r', encoding='utf-8') as f:
        # Читаем последние строки
        last_lines = f.readlines()[-lines:]

        # Объединяем строки в одну
    combined_lines = ''.join(last_lines)

    return combined_lines
