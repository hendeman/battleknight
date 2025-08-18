import os
from pathlib import Path

from dotenv import load_dotenv

# Определение всех возможных куки и их переменных окружения
COOKIE_MAPPING = {
    "BattleKnight": "BATTLEKNIGHT_COOKIE",
    "gf-cookie-consent-4449562312": "GF_CONSENT_COOKIE",
    "gf-token-production": "GF_TOKEN",
    "gf_pz_token": "GF_PZ_TOKEN",
    "pc_idt": "PC_IDT",
    "BattleKnightSession": "BATTLEKNIGHT_SESSION",
    "GTPINGRESSCOOKIE": "GTPINGRESSCOOKIE",
    "__cf_bm": "CF_BM",
    "cf_clearance": "CF_CLEARANCE",
    "OACBLOCK": "OACBLOCK",
    "OACCAP": "OACCAP",
    "OAID": "OAID",
    "OXLCA": "OXLCA"
}

# Обязательные куки (вызовут ошибку если не определены)
REQUIRED_COOKIES = ["BattleKnight", "BattleKnightSession"]


def load_custom_env(env_file=None, required_cookies=None):
    """
    Загружает .env файл и возвращает только определенные куки

    Args:
        env_file: Путь к кастомному .env файлу
        required_cookies: Список обязательных куки (None для значений по умолчанию)

    Returns:
        Словарь с куки, где определены переменные окружения

    Raises:
        FileNotFoundError: Если указанный .env файл не существует
        ValueError: Если отсутствуют обязательные куки
    """
    # Загрузка .env файла
    for env_var in COOKIE_MAPPING.values():
        os.environ.pop(env_var, None)  # Удаляем, если существует

    # Загружаем новый .env
    if env_file:
        env_path = Path(env_file)
        if not env_path.exists():
            raise FileNotFoundError(f"Env file not found: {env_file}")
        load_dotenv(env_path, override=True)
    else:
        load_dotenv()

    # Формируем словарь куки
    cookies = {
        cookie_name: os.getenv(env_var)
        for cookie_name, env_var in COOKIE_MAPPING.items()
        if os.getenv(env_var) is not None
    }

    # Проверка обязательных куки
    required = required_cookies or REQUIRED_COOKIES
    missing = [name for name in required if name not in cookies]
    if missing:
        raise ValueError(f"Missing required cookies: {missing}")
    return cookies
