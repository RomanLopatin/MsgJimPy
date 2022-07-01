"""
конфигурация клиентского логгера
"""

import logging
import os

# Создаём объект-логгер с именем app.client
CLIENT_LOG = logging.getLogger('app.client')

# Создаём объект форматирования:
CLIENT_FORMATTER = logging.Formatter("%(asctime)s %(levelname)s %(filename)s %(message)s ")

# Создаём файловый обработчик логирования:
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'app.client.log')
FILE_HANDLER = logging.FileHandler(PATH, encoding='utf-8')

# Задаем форматтер для обработчика
FILE_HANDLER.setFormatter(CLIENT_FORMATTER)

# Добавляем в логгер обработчик  и задаем уровень логгирования
CLIENT_LOG.addHandler(FILE_HANDLER)
CLIENT_LOG.setLevel(logging.DEBUG)

if __name__ == '__main__':
    CLIENT_LOG.debug('Отладочное сообщение от конф. файла')
