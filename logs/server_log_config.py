"""
конфигурация серверного логгера
"""

import logging

# Создаём объект-логгер с именем app.server
import os

SERVER_LOG = logging.getLogger('app.server')

# Создаём объект форматирования:
SERVER_FORMATTER = logging.Formatter("%(asctime)s %(levelname)s %(filename)s %(message)s ")

# Создаём файловый обработчик логирования:
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'app.server.log')
# FILE_HANDLER = logging.handlers.TimedRotatingFileHandler(PATH, encoding='utf-8', when="D", interval=1)
FILE_HANDLER = logging.FileHandler(PATH, encoding='utf-8')
# Задаем форматтер для обработчика
FILE_HANDLER.setFormatter(SERVER_FORMATTER)

# Добавляем в логгер обработчик  и задаем уровень логгирования
SERVER_LOG.addHandler(FILE_HANDLER)
SERVER_LOG.setLevel(logging.DEBUG)

if __name__ == '__main__':
    SERVER_LOG.debug('Отладочное сообщение от конф. файла')
