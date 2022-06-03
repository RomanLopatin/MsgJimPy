import json
import logging
import threading

import logs.client_log_config
import socket
import sys
import time
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_PORT, \
    DEFAULT_IP_ADDRESS, MESSAGE, MESSAGE_TEXT, SENDER, MESSAGE_RECEIVER, EXIT
from common.utils import get_message, send_message
from errors import ReqFieldMissingError
from metaclasses import ClientVerifier
from proj_decorators import func_to_log

CLIENT_LOG = logging.getLogger('app.client')


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


class Client(metaclass=ClientVerifier):
    def __init__(self, client_name, server_address, server_port):
        self.client_name = client_name
        self.server_address = server_address
        self.server_port = server_port

    @func_to_log
    def print_help(self):
        """Функция, выводящяя справку"""
        print('Поддерживаемые команды:')
        print('msg - перейти к отправке сообщения.')
        print('help - вызов справки')
        print('exit - выход')

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
        message = input('Введите сообщение для отправки или \'!!!\' для завершения работы: \n')
        if message == '!!!':
            sock.close()
            CLIENT_LOG.info('Завершение работы по команде пользователя.')
            print('Спасибо за использование нашего сервиса!')
            sys.exit(0)
        message_dict = {
            ACTION: MESSAGE,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name,
            MESSAGE_TEXT: message,
            MESSAGE_RECEIVER: message_receiver
        }
        CLIENT_LOG.debug(f'Сформировали сообщение: {message_dict}')
        return message_dict

    @func_to_log
    def send_user_message(self, client_sock):
        time.sleep(0.5)
        self.print_help()
        while True:
            command = input('Введите команду:\n')
            if command == 'msg':
                try:
                    msg_to_send = self.create_message(client_sock)
                    send_message(client_sock, msg_to_send)
                    CLIENT_LOG.info(f'Отправлено сообщение {msg_to_send} от пользователя {self.client_name}')
                except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                    CLIENT_LOG.error(f'Соединение с сервером было потеряно.')
                    sys.exit(1)
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                send_message(client_sock, self.create_exit_message())
                print('Завершение соединения.')
                CLIENT_LOG.info(f'Пользователь {self.client_name} отправил команду завершения сеанса.')
                # Задержка неоходима, чтобы успело уйти сообщение
                time.sleep(0.5)
                break
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
            try:
                message = get_message(sock)
                if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and MESSAGE_TEXT in message:

                    print(f'Получено сообщение от пользователя '
                          f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    CLIENT_LOG.info(f'Получено сообщение от пользователя '
                                    f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                else:
                    CLIENT_LOG.error(f'Получено некорректное сообщение с сервера: {message}')
            except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                CLIENT_LOG.error(f'Соединение с сервером было потеряно.')
                sys.exit(1)

    @func_to_log
    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name
        }

    def client_main(self):

        try:
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
    client = Client(client_name, server_address, server_port)
    client.client_main()


if __name__ == '__main__':
    main()
