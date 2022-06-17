import configparser

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from common.variables import SERVER_DB, RESPONSE_202, LIST_INFO, RESPONSE_400, GET_CONTACTS, ADD_CONTACT, RESPONSE_200, \
    REMOVE_CONTACT, USERS_REQUEST
import datetime

#
import json
import logging
import threading
from select import select

import logs.server_log_config
import socket
import sys, os
import time
from common.variables import ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR, \
    DEFAULT_PORT, MAX_CONNECTIONS, TIME, MESSAGE_TEXT, MESSAGE, SENDER, MESSAGE_RECEIVER, EXIT

from common.utils import get_message, send_message
from descriptors import PortDescriptor
from errors import IncorrectDataRecivedError
from metaclasses import ServerVerifier
from proj_decorators import func_to_log

from server_db import ServerStorage
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


class Server(threading.Thread, metaclass=ServerVerifier):
    port_to_listen = PortDescriptor()

    def __init__(self, port_to_listen, address_to_listen, database):
        self.port_to_listen = port_to_listen
        self.address_to_listen = address_to_listen

        # Инициализация пустого списка клиентов
        self.all_client_socks = []

        self.messages = []

        self.names = dict()  # {client_name: client_socket}

        # База данных сервера
        self.database = database

        # Конструктор предка
        super().__init__()

    def socket_init(self):
        # Инициализация сокета и обмен
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.address_to_listen, self.port_to_listen))
        sock.settimeout(0.5)
        self.serv_sock = sock
        self.serv_sock.listen(MAX_CONNECTIONS)

    def run(self):

        self.socket_init()

        while True:
            try:
                client_sock, client_address = self.serv_sock.accept()
                SERVER_LOG.info(f'Установили соедение с клиентом по адресу: {client_address}')
            except OSError as err:
                pass
            else:
                print(f"Получен запрос на соединение от {str(client_address)}")
                SERVER_LOG.debug(f"Получен запрос на соединение от {client_address}")
                self.all_client_socks.append(client_sock)
            wait = 0
            client_socks_to_read = []
            client_socks_to_write = []
            try:
                if self.all_client_socks:
                    client_socks_to_read, client_socks_to_write, errors = select(self.all_client_socks,
                                                                                 self.all_client_socks, [], wait)
            except OSError as err:
                SERVER_LOG.error(f'Ошибка работы с сокетами: {err}')

            if client_socks_to_read:
                for client_sock_to_read in client_socks_to_read:
                    message_from_client = ''
                    try:
                        # message_from_client = get_message(client_sock_to_read)
                        # print(f'Получено сообщение от клиента: {message_from_client}')
                        SERVER_LOG.debug(f'Получено сообщение от клиента: {message_from_client}')
                        self.process_client_message(get_message(client_sock_to_read), self.messages,
                                                    client_sock_to_read,
                                                    self.all_client_socks, self.names)
                    except Exception as e:
                        print(e)
                        SERVER_LOG.info(f'Клиент {client_sock_to_read.getpeername()} отключился от сервера.')
                        self.all_client_socks.remove(client_sock_to_read)

                # Если есть сообщения для отправки и ожидающие клиенты, отправляем им сообщение.
            if self.messages and client_socks_to_write:
                msg_receiver = self.messages[0][2]
                try:
                    client_sock_to_write = self.names[msg_receiver]
                except KeyError:
                    SERVER_LOG.info(f'Клиент c именем {msg_receiver} не зарегистрирован!')
                    print(f' Неверные данные получателя. Клиент c именем {msg_receiver} не зарегистрирован!')
                    del self.messages[0]
                else:
                    if client_sock_to_write in client_socks_to_write:
                        message = {
                            ACTION: MESSAGE,
                            SENDER: self.messages[0][0],
                            TIME: time.time(),
                            MESSAGE_TEXT: self.messages[0][1],
                            MESSAGE_RECEIVER: msg_receiver
                        }
                        del self.messages[0]

                        try:
                            send_message(client_sock_to_write, message)
                            print(f'Клиенту {client_sock_to_write.getpeername()} отправлено сообщение {message}')
                        except:
                            SERVER_LOG.info(f'Клиент {client_sock_to_write.getpeername()} отключился от сервера.')
                            client_sock_to_write.close()
                            self.all_client_socks.remove(client_sock_to_write)

    @func_to_log
    def process_client_message(self, message, messages_list, client, all_client_socks, names):
        global new_connection
        SERVER_LOG.debug(f'Вызов ф-ии process_client_message(). Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии (PRESENCE), принимаем его и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
                and USER in message:
            acc_name = message[USER][ACCOUNT_NAME]
            if acc_name not in names.keys():
                names[acc_name] = client
                SERVER_LOG.debug(f'Добавили запись в таблицу имен : {acc_name}: {names[acc_name]}')
                client_ip, client_port = client.getpeername()
                self.database.user_login(acc_name, client_ip, client_port)
                SERVER_LOG.debug(f'Добавили запись о новом пользователе таблицу БД user_login :'
                                 f' username/ip_address/port : {acc_name}/{client_ip}/{client_port}')
                msg = {RESPONSE: 200}
                send_message(client, msg)
                with conflag_lock:
                    new_connection = True
            else:
                response = {RESPONSE: 400, ERROR: 'Имя пользователя уже занято.'}
                send_message(client, response)
                all_client_socks.remove(client)
                client.close()
            return
        # Если это сообщение (MESSAGE), то добавляем его в список сообщений.
        elif ACTION in message and message[ACTION] == MESSAGE and \
                TIME in message and MESSAGE_TEXT in message and message[MESSAGE_RECEIVER]:
            messages_list.append((message[ACCOUNT_NAME], message[MESSAGE_TEXT], message[MESSAGE_RECEIVER]))
            return
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.user_logout(message[ACCOUNT_NAME])
            all_client_socks.remove(names[message[ACCOUNT_NAME]])
            names[message[ACCOUNT_NAME]].close()
            del names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return
        # Если это запрос контакт-листа
        elif ACTION in message and message[ACTION] == GET_CONTACTS and USER in message and \
                self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            send_message(client, response)

            # Если это добавление контакта
        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)
        # Если это удаление контакта
        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)
        # Если это запрос известных пользователей
        elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0]
                                   for user in self.database.users_list()]
            send_message(client, response)
        else:
            msg = {
                RESPONSE: 400,
                ERROR: 'Bad request'
            }
            send_message(msg, client)
            return


def print_help():
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    config = configparser.ConfigParser()

    # dir_path = os.path.dirname(os.path.realpath(__file__))
    ini_path = os.path.join(os.getcwd(), 'server.ini')
    config.read(ini_path)
    # print(config['SETTINGS']['default_port'])

    database = ServerStorage()

    address_to_listen, port_to_listen = serv_arg_parser()
    server = Server(port_to_listen, address_to_listen, database)
    server.daemon = True
    server.start()

    # print_help()
    #
    # # Основной цикл сервера:
    # while True:
    #     command = input('Введите команду: ')
    #     if command == 'help':
    #         print_help()
    #     elif command == 'exit':
    #         break
    #     elif command == 'users':
    #         for user in sorted(database.users_list()):
    #             print(f'Пользователь {user[0]}, последний вход: {user[1]}')
    #     elif command == 'connected':
    #         active_users = database.active_users_list()
    #         if active_users:
    #             for user in sorted(active_users):
    #                 print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
    #         else:
    #             print('Активные пользователи отсутствуют.')
    #     elif command == 'loghist':
    #         name = input('Введите имя пользователя для просмотра истории.\n '
    #                      'Для вывода всей истории, просто нажмите Enter: ')
    #         for user in sorted(database.login_history(name)):
    #             print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
    #     else:
    #         print('Команда не распознана.')

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
