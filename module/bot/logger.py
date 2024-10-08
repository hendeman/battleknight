import logging
import telebot


def setup_logging():
    logging.basicConfig(filename='telebot.log',
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    telebot.logger.setLevel(logging.INFO)  # Уровни: DEBUG, INFO, WARNING, ERROR, CRITICAL
