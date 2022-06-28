import argparse
import sys
import os
import configparser
import threading

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from common.proj_decorators import func_to_log
from server.server_db import ServerStorage
from server.core import Server
from common.variables import DEFAULT_PORT
from server.main_window import MainWindow

import logging
import server.logs.server_log_config
SERVER_LOG = logging.getLogger('app.server')

new_connection = False
conflag_lock = threading.Lock()


@func_to_log
def serv_arg_parser(default_port, default_address):
    """Парсер аргументов коммандной строки."""
    SERVER_LOG.debug(
        f'Инициализация парсера аргументов коммандной строки: {sys.argv}')
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    parser.add_argument('--no_gui', action='store_true')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    gui_flag = namespace.no_gui
    SERVER_LOG.debug('Аргументы успешно загружены.')
    return listen_address, listen_port, gui_flag
# def serv_arg_parser():
#     """
#            Сперва пытаемся обработать параметры командной строки (address_to_listen и port_to_listen).
#            Если не удается - используем значения по умолчанию
#            server.py -p 8888 -a 127.0.0.1
#            """
#     try:
#         if '-p' in sys.argv:
#             port_to_listen = sys.argv[sys.argv.index('-p') + 1]
#         else:
#             port_to_listen = DEFAULT_PORT
#     except IndexError:
#         SERVER_LOG.error('Index error (port value should be defined!)')
#         sys.exit(1)
#
#     try:
#         if '-a' in sys.argv:
#             address_to_listen = sys.argv[sys.argv.index('-a') + 1]
#         else:
#             address_to_listen = ''
#     except IndexError:
#         SERVER_LOG.error('Index error (address)')
#         sys.exit(1)
#
#     msg_for_log = f'Запускаем сервер, порт для подключений: {port_to_listen}, ' \
#                   f'адрес с которого принимаются подключения: {address_to_listen}.'
#
#     SERVER_LOG.info(msg_for_log)
#     # print(msg_for_log)
#
#     return address_to_listen, port_to_listen


def print_help():
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    config = configparser.ConfigParser()
    ini_path = os.path.join(os.getcwd(), 'server.ini')
    config.read(ini_path)

    database = ServerStorage(
        os.path.join(
            config['SETTINGS']['Database_path'],
            config['SETTINGS']['Database_file'])
    )

    address_to_listen, port_to_listen, gui_flag = serv_arg_parser(
        config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])
    server = Server(address_to_listen, port_to_listen, database)
    server.daemon = True
    server.start()

    server_app = QApplication(sys.argv)
    main_window = MainWindow(database, server, config)

    # Запускаем GUI
    server_app.exec_()


if __name__ == '__main__':
    main()
