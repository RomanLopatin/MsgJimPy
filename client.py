import argparse
import logging
import threading

import sys

from PyQt5.QtWidgets import QApplication

from client.client_db import ClientDatabase
from client.main_window import ClientMainWindow
from client.start_dialog import UserNameDialog
from client.transport import ClientTransport
from common.variables import DEFAULT_PORT, DEFAULT_IP_ADDRESS
from common.errors import ServerError
from common.proj_decorators import func_to_log

import logging
import client.logs.client_log_config

CLIENT_LOG = logging.getLogger('app.client')

sock_lock = threading.Lock()
database_lock = threading.Lock()


# @func_to_log
# def client_arg_parser():
#     client_name = ''
#     client_passwd = ''
#     try:
#         client_name = sys.argv[sys.argv.index('-n') + 1]
#     except (IndexError, ValueError):
#         pass
#
#     try:
#         server_address = sys.argv[1]
#         server_port = int(sys.argv[2])
#         if server_port < 1024 or server_port > 65535:
#             CLIENT_LOG.critical(
#                 f'Попытка запуска клиента с неверным портом ({server_port}). '
#                 f'Требуется диапазон от 1024 до 65535!')
#     except IndexError:
#         CLIENT_LOG.error("Index error. Не удалось получить значение порта/сервера по индексу."
#                          "Будут использованы значения по умолчанию.")
#         server_address = DEFAULT_IP_ADDRESS
#         server_port = DEFAULT_PORT
#     CLIENT_LOG.info(f'Запущен клиент с парамертами: '
#                     f'адрес сервера: {server_address}, порт: {server_port}')

#   return client_name, server_address, server_port, client_passwd


@func_to_log
def client_arg_parser():
    """
    Парсер аргументов командной строки, возвращает кортеж из 4 элементов
    адрес сервера, порт, имя пользователя, пароль.
    Выполняет проверку на корректность номера порта.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_passwd = namespace.password

    # проверим подходящий номер порта
    if not 1023 < server_port < 65536:
        CLIENT_LOG.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}. '
            f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
        exit(1)

    return client_name, server_address, server_port, client_passwd


def main():
    client_name, server_address, server_port, client_passwd = client_arg_parser()

    # Создаём клиентокое приложение
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке, то запросим его
    start_dialog = UserNameDialog()
    start_dialog.client_name.insert(client_name)
    start_dialog.client_passwd.insert(client_passwd)

    client_app.exec_()
    # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и
    # удаляем объект, инааче выходим
    if start_dialog.ok_pressed:
        client_name = start_dialog.client_name.text()
        client_passwd = start_dialog.client_passwd.text()
        CLIENT_LOG.debug(f'Using USERNAME = {client_name}, PASSWD = {client_passwd}.')
    else:
        exit(0)

    # Записываем логи
    CLIENT_LOG.info(
        f'Запущен клиент с параметрами: адрес сервера: {server_address} , порт: {server_port},'
        f' имя пользователя: {client_name}')

    # Инициализация БД
    database = ClientDatabase(client_name)

    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientTransport(server_port, server_address, database, client_name, client_passwd)
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
