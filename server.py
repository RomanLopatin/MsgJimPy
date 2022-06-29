import argparse
import sys
import os
import configparser
import threading
import logging

from PyQt5.QtWidgets import QApplication, QMessageBox

from common.proj_decorators import func_to_log
from server.server_db import ServerStorage
from server.core import Server
from server.main_window import MainWindow
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
    server_ = Server(address_to_listen, port_to_listen, database)
    server_.daemon = True
    server_.start()

    server_app = QApplication(sys.argv)
    main_window = MainWindow(database, server_, config)

    # Запускаем GUI
    server_app.exec_()


if __name__ == '__main__':
    main()
