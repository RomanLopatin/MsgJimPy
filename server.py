import configparser

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox
from common.variables import RESPONSE_202, LIST_INFO, GET_CONTACTS, ADD_CONTACT, RESPONSE_200, \
    RESPONSE_400, REMOVE_CONTACT, USERS_REQUEST

#
import logging
import threading
from select import select

import socket
import sys, os
import time
from common.variables import ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR, \
    DEFAULT_PORT, MAX_CONNECTIONS, TIME, MESSAGE_TEXT, MESSAGE, SENDER, MESSAGE_RECEIVER, EXIT

from common.utils import get_message, send_message
from descriptors import PortDescriptor
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
        # Инициализация Сокета
        global new_connection
        self.socket_init()

        # Основной цикл программы сервера
        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.serv_sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOG.info(f'Установлено соедение с ПК {client_address}')
                self.all_client_socks.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.all_client_socks:
                    recv_data_lst, send_data_lst, err_lst = select(self.all_client_socks,
                                                                          self.all_client_socks, [], 0)
            except OSError as err:
                SERVER_LOG.error(f'Ошибка работы с сокетами: {err}')

            # принимаем сообщения и если ошибка, исключаем клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(get_message(client_with_message),
                                                    client_with_message)
                    except OSError:
                        # Ищем клиента в словаре клиентов
                        # и удаляем его из него и базы подключённых
                        SERVER_LOG.info(f'Клиент {client_with_message.getpeername()} '
                                    f'отключился от сервера.')
                        for name in self.names:
                            if self.names[name] == client_with_message:
                                self.database.user_logout(name)
                                del self.names[name]
                                break
                        self.clients.remove(client_with_message)
                        with conflag_lock:
                            new_connection = True

            # Если есть сообщения, обрабатываем каждое.
            for message in self.messages:
                try:
                    self.process_message(message, send_data_lst)
                except (ConnectionAbortedError, ConnectionError,
                        ConnectionResetError, ConnectionRefusedError):
                    SERVER_LOG.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[message[DESTINATION]])
                    self.database.user_logout(message[DESTINATION])
                    del self.names[message[DESTINATION]]
                    with conflag_lock:
                        new_connection = True
            self.messages.clear()

    # Функция адресной отправки сообщения определённому клиенту.
    # Принимает словарь сообщение, список зарегистрированых
    # пользователей и слушающие сокеты. Ничего не возвращает.
    def process_message(self, message, listen_socks):
        if message[MESSAGE_RECEIVER] in self.names \
                and self.names[message[MESSAGE_RECEIVER]] in listen_socks:
            send_message(self.names[message[MESSAGE_RECEIVER]], message)
            SERVER_LOG.info(f'Отправлено сообщение пользователю {message[MESSAGE_RECEIVER]} '
                        f'от пользователя {message[SENDER]}.')
        elif message[MESSAGE_RECEIVER] in self.names and \
                self.names[message[MESSAGE_RECEIVER]] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOG.error(
                f'Пользователь {message[MESSAGE_RECEIVER]} '
                f'не зарегистрирован на сервере, отправка сообщения невозможна.')

    # Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
    # проверяет корректность, отправляет
    #     словарь-ответ в случае необходимости.
    def process_client_message(self, message, client):
        global new_connection
        SERVER_LOG.debug(f'Разбор сообщения от клиента : {message}')

        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE \
                and TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован, регистрируем,
            # иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
                with conflag_lock:
                    new_connection = True
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.all_client_socks.remove(client)
                client.close()
            return

        # Если это сообщение, то добавляем его в очередь сообщений,
        # проверяем наличие в сети. и отвечаем.
        elif ACTION in message \
                and message[ACTION] == MESSAGE \
                and MESSAGE_RECEIVER in message \
                and TIME in message \
                and SENDER in message \
                and MESSAGE_TEXT in message \
                and self.names[message[SENDER]] == client:
            if message[MESSAGE_RECEIVER] in self.names:
                self.messages.append(message)
                self.database.process_message(message[SENDER], message[MESSAGE_RECEIVER])
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                send_message(client, response)
            return

        # Если клиент выходит
        elif ACTION in message \
                and message[ACTION] == EXIT \
                and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.database.user_logout(message[ACCOUNT_NAME])
            SERVER_LOG.info(f'Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.')
            self.all_client_socks.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
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
        elif ACTION in message \
                and message[ACTION] == ADD_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # Если это удаление контакта
        elif ACTION in message \
                and message[ACTION] == REMOVE_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # Если это запрос известных пользователей
        elif ACTION in message \
                and message[ACTION] == USERS_REQUEST \
                and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in self.database.users_list()]
            send_message(client, response)

        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
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
