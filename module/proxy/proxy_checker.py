import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from logs.logs import p_log, setup_logging

# Получаем директорию, где лежит этот скрипт
MODULE_DIR = Path(__file__).parent

# Теперь строим пути относительно этой директории
FILE_PATH = MODULE_DIR / 'proxies.txt'
FILE_PATH_RESULT = MODULE_DIR / 'proxy_results.txt'

TEST_URLS = {
    'ip': 'https://api.ipify.org?format=json',
    'headers': 'http://httpbin.org/headers'
}


def check_proxy_anonymity(proxy, timeout=5):
    """
    Проверяет уровень анонимности прокси через headers.astral.ninja
    :param proxy: строка в формате 'ip:port' или 'user:pass@ip:port'
    :param timeout: таймаут соединения в секундах
    :return: словарь с результатами проверки анонимности
    """
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }

    try:
        response = requests.get(
            TEST_URLS['headers'],
            proxies=proxies,
            timeout=timeout
        )
        response.raise_for_status()

        headers = response.headers
        revealing_headers = [
            ('Via', 'прокси раскрывает себя через заголовок Via'),
            ('X-Forwarded-For', 'прокси раскрывает реальный IP через X-Forwarded-For'),
            ('X-Real-Ip', 'прокси раскрывает реальный IP через X-Real-Ip')
        ]

        anonymity_issues = []
        for header, message in revealing_headers:
            if header in headers:
                anonymity_issues.append(message)

        if anonymity_issues:
            return {
                'anonymous': False,
                'anonymity_level': 'transparent',
                'issues': anonymity_issues,
                'headers': headers
            }
        else:
            return {
                'anonymous': True,
                'anonymity_level': 'elite' if 'я' not in headers else 'anonymous',
                'issues': [],
                'headers': headers
            }

    except requests.exceptions.RequestException as e:
        return {
            'anonymous': False,
            'anonymity_level': 'unknown',
            'issues': [f'Ошибка проверки анонимности: {str(e)}'],
            'headers': None
        }


def check_proxy(proxy, timeout=5):
    """Проверяет прокси на работоспособность и анонимность."""
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }

    # Шаг 1: Получаем реальный IP БЕЗ прокси
    try:
        real_ip_response = requests.get(TEST_URLS['ip'], timeout=timeout)
        real_ip = real_ip_response.json().get('ip', '')
    except Exception as e:
        return {'error': f'Не удалось получить реальный IP: {str(e)}'}

    # Шаг 2: Проверяем прокси через api.ipify.org
    try:
        proxy_ip_response = requests.get(
            TEST_URLS['ip'],
            proxies=proxies,
            timeout=timeout
        )
        proxy_ip = proxy_ip_response.json().get('ip', '')

        # Шаг 3: Проверяем анонимность
        anonymity_check = check_proxy_anonymity(proxy, timeout)

        # Проверяем, не вернул ли прокси наш реальный IP
        if real_ip == proxy_ip:
            anonymity_check.update({
                'anonymous': False,
                'anonymity_level': 'transparent',
                'issues': anonymity_check.get('issues', []) +
                          [f'Прокси вернул реальный IP: {real_ip}']
            })

        return {
            'proxy': proxy,
            'works': True,
            'external_ip': proxy_ip,
            'real_ip': real_ip,
            'anonymous': anonymity_check['anonymous'],
            'anonymity_level': anonymity_check['anonymity_level'],
            'issues': anonymity_check.get('issues', []),
            'response_time': proxy_ip_response.elapsed.total_seconds()
        }

    except Exception as e:
        return {
            'proxy': proxy,
            'works': False,
            'error': str(e)
        }


def check_proxies_from_file(file_path, max_workers=10):
    """
    Проверяет список прокси из файла
    :param file_path: путь к файлу с прокси (по одному на строку)
    :param max_workers: количество потоков для параллельной проверки
    :return: список словарей с результатами проверки
    """
    with open(file_path, 'r') as f:
        proxies = [line.strip() for line in f if line.strip()]

    working_proxies = []
    anonymous_proxies = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(check_proxy, proxies))

    working_proxies = [r for r in results if r.get('works')]
    anonymous_proxies = [r for r in working_proxies if r.get('anonymous')]
    failed_proxies = [r for r in results if not r.get('works')]
    non_anonymous_proxies = [r for r in working_proxies if not r.get('anonymous')]

    p_log(f"\nПроверено прокси: {len(results)}")
    p_log(f"Рабочих прокси: {len(working_proxies)}")
    p_log(f"  - Анонимных: {len(anonymous_proxies)}")
    p_log(f"  - Не анонимных: {len(non_anonymous_proxies)}")
    p_log(f"Не рабочих прокси: {len(failed_proxies)}\n")

    if anonymous_proxies:
        p_log("Топ 10 самых быстрых анонимных прокси:")
        for proxy in sorted(anonymous_proxies, key=lambda x: x.get('response_time', 999))[:10]:
            p_log(
                f"{proxy.get('proxy')} - {proxy.get('response_time')}s - IP: {proxy.get('external_ip')} - Уровень: {proxy.get('anonymity_level')}")
    else:
        p_log("Анонимные прокси не найдены!")

    return results


def save_proxy_txt(results):
    try:
        # Сохраняем результаты в файл
        with open(FILE_PATH_RESULT, 'w') as f:
            for res in results:
                status = "WORKING" if res.get('works') else "FAILED"
                anonymity = ""
                if res.get('works'):
                    anonymity = "ANONYMOUS" if res.get('anonymous') else "NOT ANONYMOUS"
                    anonymity += f" ({res.get('anonymity_level')})"

                f.write(f"{res.get('proxy')} - {status}")
                if res.get('works'):
                    f.write(f" - {anonymity}")
                    f.write(f" - {res.get('response_time')}s - {res.get('external_ip')}")
                    if res.get('issues'):
                        f.write(f" - Проблемы: {', '.join(res.get('issues'))}")
                else:
                    f.write(f" - ERROR: {res.get('error')}")
                f.write("\n")

        p_log(f"Результаты сохранены в {FILE_PATH_RESULT}")

    except FileNotFoundError:
        p_log(f"Ошибка: файл {FILE_PATH_RESULT} не найден")
    except Exception as e:
        p_log(f"Произошла ошибка: {str(e)}")


def clear_proxy_list(lst):
    proxy_list = []
    for proxy in lst:
        if proxy.get('anonymity_level') == 'elite':
            proxy_list.append(proxy.get('proxy'))
    return proxy_list


def proxy_checker(max_workers=20):
    results = check_proxies_from_file(FILE_PATH, max_workers)
    save_proxy_txt(results)
    return clear_proxy_list(results)


if __name__ == "__main__":
    setup_logging()
    print(proxy_checker())
