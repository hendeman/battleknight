from datetime import datetime

from logs.logs import p_log
from module.all_function import get_config_value


class RubyManager:
    def __init__(self):
        self.total_limit = get_config_value("rubies_limit")
        self.daily_limit = get_config_value("rubies_day")
        self.total_used = 0
        self.daily_used = 0
        self.last_reset_date = datetime.now().date()

    def should_use_rubies(self):
        # Проверяем смену дня
        if datetime.now().date() != self.last_reset_date:
            self.daily_used = 0
            self.last_reset_date = datetime.now().date()
            p_log("Новый день, сбрасываем счетчик рубинов")

        # Возвращаем True если можно использовать рубины
        return self.daily_used < self.daily_limit and self.total_used < self.total_limit

    def mark_ruby_used(self):
        self.total_used += 1
        self.daily_used += 1


ruby_manager = RubyManager()
