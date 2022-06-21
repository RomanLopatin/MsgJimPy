import json
import logging
import threading

import socket
import sys
import time

from client.client_db import ClientDatabase
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_PORT, \
    DEFAULT_IP_ADDRESS, MESSAGE, MESSAGE_TEXT, SENDER, MESSAGE_RECEIVER, EXIT, USERS_REQUEST, LIST_INFO, REMOVE_CONTACT, \
    ADD_CONTACT, GET_CONTACTS
from common.utils import get_message, send_message
from common.errors import ReqFieldMissingError, IncorrectDataRecivedError, ServerError
from metaclasses import ClientVerifier
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


def contacts_list_request(sock, name):
    CLIENT_LOG.debug(f'Запрос контакт листа для пользователя {name}')
    req = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        USER: name
    }
    CLIENT_LOG.debug(f'Сформирован запрос {req}')
    send_message(sock, req)
    ans = get_message(sock)
    CLIENT_LOG.debug(f'Получен ответ {ans}')
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Функция добавления пользователя в контакт лист
def add_contact(sock, username, contact):
    CLIENT_LOG.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта')
    print('Удачное создание контакта.')


# Функция запроса списка известных пользователей
def user_list_request(sock, username):
    CLIENT_LOG.debug(f'Запрос списка известных пользователей {username}')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Функция удаления пользователя из списка контактов
def remove_contact(sock, username, contact):
    CLIENT_LOG.debug(f'Создание контакта {contact}')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')


# Функция инициализатор базы данных.
# Запускается при запуске, загружает данные в базу с сервера.
@func_to_log
def database_load(sock, database, username):
    # Загружаем список известных пользователей
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        CLIENT_LOG.error('Ошибка запроса списка известных пользователей.')
    else:
        database.add_users(users_list)

    # # Загружаем список контактов
    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        CLIENT_LOG.error('Ошибка запроса списка контактов.')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


class Client(metaclass=ClientVerifier):
    def __init__(self, client_name, server_address, server_port, database):
        self.client_name = client_name
        self.server_address = server_address
        self.server_port = server_port
        self.database = database

    @func_to_log
    def print_help(self):
        print('Поддерживаемые команды:')
        print('msg - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('history - история сообщений')
        print('contacts - список контактов')
        print('edit - редактирование списка контактов')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    @func_to_log
    def create_presence(self):
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.client_name
            }
        }
        CLIENT_LOG.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.client_name}')
        return out

    @func_to_log
    def create_message(self, sock):
        """Функция запрашивает текст сообщения и возвращает его.
        Так же завершает работу при вводе подобной комманды
        """
        message_receiver = input("Введите имя получателя сообщения: \n")
        message = input('Введите сообщение для отправки \n')

        # Проверим, что получатель существует
        with database_lock:
            if not self.database.check_user(message_receiver):
                CLIENT_LOG.error(f'Попытка отправить сообщение '
                             f'незарегистрированому получателю: {message_receiver}')
                return

        message_dict = {
            ACTION: MESSAGE,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name,
            MESSAGE_TEXT: message,
            MESSAGE_RECEIVER: message_receiver
        }
        CLIENT_LOG.debug(f'Сформировали сообщение: {message_dict}')

        with database_lock:
            self.database.save_message(self.client_name, message_receiver, message)

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with sock_lock:
            try:
                send_message(sock, message_dict)
                CLIENT_LOG.info(f'Отправлено сообщение от {self.client_name} для {message_receiver}')
            except OSError as err:
                if err.errno:
                    CLIENT_LOG.critical('Потеряно соединение с сервером.')
                    exit(1)
                else:
                    CLIENT_LOG.error('Не удалось передать сообщение. Таймаут соединения')

    @func_to_log
    def send_user_message(self, client_sock):
        time.sleep(0.5)
        CLIENT_LOG.debug('Зашли в функцию Send_user_message.')
        self.print_help()
        while True:
            command = input('Введите команду:\n')
            if command == 'msg':
                self.create_message(client_sock)
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                try:
                    send_message(client_sock, self.create_exit_message())
                except Exception as e:
                    print(e)
                print('Завершение соединения.')
                CLIENT_LOG.info(f'Пользователь {self.client_name} отправил команду завершения сеанса.')
                # Задержка неоходима, чтобы успело уйти сообщение
                time.sleep(0.5)
                break
                # Список контактов
            elif command == 'contacts':
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)

            # Редактирование контактов
            elif command == 'edit':
                self.edit_contacts(client_sock)

            # история сообщений.
            elif command == 'history':
                self.print_history()
            else:
                print('Команда не распознана, попробойте снова.')
                self.print_help()

    @func_to_log
    def process_answer(self, message):
        CLIENT_LOG.debug(f'Обработка сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200:OK'
            else:
                return f'400: {message[ERROR]}'
        CLIENT_LOG.error(f'{ReqFieldMissingError(RESPONSE)}')
        raise ReqFieldMissingError(RESPONSE)

    @func_to_log
    def message_from_server(self, sock):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # Если не сделать тут задержку,
            # то второй поток может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(sock)
                except IncorrectDataRecivedError:
                    CLIENT_LOG.error(f'Не удалось декодировать полученное сообщение.')
                except OSError as err:
                    if err.errno:
                        CLIENT_LOG.critical(f'Потеряно соединение с сервером.')
                        break
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                    CLIENT_LOG.error(f'Соединение с сервером было потеряно.')
                    break
                    # sys.exit(1)
                else:
                    if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and MESSAGE_TEXT in \
                            message:
                        print(f'Получено сообщение от пользователя '
                              f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                        CLIENT_LOG.info(f'Получено сообщение от пользователя '
                                        f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    else:
                        CLIENT_LOG.error(f'Получено некорректное сообщение с сервера: {message}')

    @func_to_log
    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name
        }

    # Функция выводящяя историю сообщений
    def print_history(self):
        ask = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock:
            if ask == 'in':
                history_list = self.database.get_history(to_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} '
                          f'от {message[3]}:\n{message[2]}')
            elif ask == 'out':
                history_list = self.database.get_history(from_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} '
                          f'от {message[3]}:\n{message[2]}')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]},'
                          f' пользователю {message[1]} '
                          f'от {message[3]}\n{message[2]}')

    # Функция изменеия контактов
    def edit_contacts(self, client_sock):
        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            edit = input('Введите имя удаляемного контакта: ')
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    CLIENT_LOG.error('Попытка удаления несуществующего контакта.')
        elif ans == 'add':
            # Проверка на возможность такого контакта
            edit = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
            with sock_lock:
                try:
                    add_contact(client_sock, self.client_name, edit)
                except ServerError:
                    CLIENT_LOG.error('Не удалось отправить информацию на сервер.')

    def client_main(self):
        try:
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.settimeout(10)  # макс время ожидания блокир. методов сокета
            client_sock.connect((self.server_address, self.server_port))
            msg_to_server = self.create_presence()

            send_message(client_sock, msg_to_server)
            answer = self.process_answer(get_message(client_sock))
            CLIENT_LOG.info(f"Получен ответ от сервера: {answer}")
        except json.JSONDecodeError:
            CLIENT_LOG.error('Не удалось декодировать полученную Json строку.')
        except ReqFieldMissingError as missing_error:
            CLIENT_LOG.error(f'В ответе сервера отсутствует необходимое поле '
                             f'{missing_error.missing_field}')
        except ConnectionRefusedError:
            CLIENT_LOG.critical(f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                                f'конечный компьютер отверг запрос на подключение.')
        else:
            # Инициализация БД
            database_load(client_sock, self.database, self.client_name)

            # Если соединение с сервером установлено,
            # # 1.запускаем поток приёма сообщений
            receiver = threading.Thread(target=self.message_from_server, args=(client_sock,))
            receiver.daemon = True
            receiver.start()
            CLIENT_LOG.debug(f'Клиентом {self.client_name}  запущен поток приема сообщений')
            print(f'Клиентом {self.client_name}  запущен поток приема сообщений')

            # 2.запускаем поток отправки сообщений
            user_sender = threading.Thread(target=self.send_user_message, args=(client_sock,))
            user_sender.daemon = True
            user_sender.start()
            CLIENT_LOG.debug(f'Клиентом {self.client_name}  запущен поток отправки сообщений')
            print(f'Клиентом {self.client_name}  запущен поток отправки сообщений')

            while True:
                time.sleep(1)
                if receiver.is_alive() and user_sender.is_alive():
                    continue
                if not receiver.is_alive():
                    CLIENT_LOG.debug(f'Поток приема сообщений клиента {self.client_name} не живой. Закрываем его!')
                if not user_sender.is_alive():
                    CLIENT_LOG.debug(f'Поток отправки сообщений клиента {self.client_name} не живой. Закрываем его!')
                break


def main():
    client_name, server_address, server_port = client_arg_parser()
    database = ClientDatabase(client_name)
    client = Client(client_name, server_address, server_port, database)
    client.client_main()


if __name__ == '__main__':
    main()
