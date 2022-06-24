import sys
import os
import configparser
import logging
import threading

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from proj_decorators import func_to_log
from server.server_db import ServerStorage
from server.core import Server
from common.variables import DEFAULT_PORT
from server_gui import MainWindow, gui_create_model, HistoryWindow, ConfigWindow, create_stat_model

SERVER_LOG = logging.getLogger('app.server')

new_connection = False
conflag_lock = threading.Lock()


@func_to_log
def serv_arg_parser():
    """
           Сперва пытаемся обработать параметры командной строки (address_to_listen и port_to_listen).
           Если не удается - используем значения по умолчанию
           server.py -p 8888 -a 127.0.0.1
           """
    try:
        if '-p' in sys.argv:
            port_to_listen = sys.argv[sys.argv.index('-p') + 1]
        else:
            port_to_listen = DEFAULT_PORT
    except IndexError:
        SERVER_LOG.error('Index error (port value should be defined!)')
        sys.exit(1)

    try:
        if '-a' in sys.argv:
            address_to_listen = sys.argv[sys.argv.index('-a') + 1]
        else:
            address_to_listen = ''
    except IndexError:
        SERVER_LOG.error('Index error (address)')
        sys.exit(1)

    msg_for_log = f'Запускаем сервер, порт для подключений: {port_to_listen}, ' \
                  f'адрес с которого принимаются подключения: {address_to_listen}.'

    SERVER_LOG.info(msg_for_log)
    # print(msg_for_log)

    return address_to_listen, port_to_listen


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

    database = ServerStorage()

    address_to_listen, port_to_listen = serv_arg_parser()
    server = Server(port_to_listen, address_to_listen, database)
    server.daemon = True
    server.start()

    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # Инициализируем параметры в окна
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    # Функция, обновляющая список подключённых, проверяет флаг подключения, и
    # если надо обновляет список
    def list_update():
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(
                gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    # Функция, создающая окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    # Функция создающяя окно с настройками сервера.
    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    # Функция сохранения настроек
    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()


if __name__ == '__main__':
    main()
