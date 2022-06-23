import json
import logging
import threading

import socket
import sys
import time

from PyQt5.QtWidgets import QApplication

from client.client_db import ClientDatabase
from client.main_window import ClientMainWindow
from client.transport import ClientTransport
from common.variables import  DEFAULT_PORT, DEFAULT_IP_ADDRESS
from common.errors import ReqFieldMissingError, IncorrectDataRecivedError, ServerError
from proj_decorators import func_to_log

CLIENT_LOG = logging.getLogger('app.client')

sock_lock = threading.Lock()
database_lock = threading.Lock()


@func_to_log
def client_arg_parser():
    client_name = ''
    try:
        client_name = sys.argv[sys.argv.index('-n') + 1]
    except (IndexError, ValueError):
        client_name = input("Введите имя клиента: ")
    if not client_name:
        CLIENT_LOG.critical('Не задано имя клиента!')
        sys.exit(1)

    try:
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        if server_port < 1024 or server_port > 65535:
            CLIENT_LOG.critical(
                f'Попытка запуска клиента с неверным портом ({server_port}). '
                f'Требуется диапазон от 1024 до 65535!')
    except IndexError:
        CLIENT_LOG.error("Index error. Не удалось получить значение порта/сервера по индексу."
                         "Будут использованы значения по умолчанию.")
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
    CLIENT_LOG.info(f'Запущен клиент с парамертами: '
                    f'адрес сервера: {server_address}, порт: {server_port}')

    return client_name, server_address, server_port


def main():
    client_name, server_address, server_port = client_arg_parser()

    # Создаём клиентокое приложение
    client_app = QApplication(sys.argv)

    # Инициализация БД
    database = ClientDatabase(client_name)

    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientTransport(server_port, server_address, database, client_name)
    except ServerError as error:
        print(error.text)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    # Создаём GUI
    main_window = ClientMainWindow(database, transport)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат Программа alpha release - {client_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт
    transport.transport_shutdown()
    transport.join()


if __name__ == '__main__':
    main()
