import json
import logging
import logs.client_log_config
import socket
import sys
import time
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_PORT, \
    DEFAULT_IP_ADDRESS, MESSAGE, MESSAGE_TEXT, SENDER
from common.utils import get_message, send_message
from errors import ReqFieldMissingError
from proj_decorators import func_to_log

CLIENT_LOG = logging.getLogger('app.client')


@func_to_log
def create_presence(account_name='Guest'):
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    CLIENT_LOG.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
    return out


@func_to_log
def create_message(sock, account_name='Guest'):
    """Функция запрашивает текст сообщения и возвращает его.
    Так же завершает работу при вводе подобной комманды
    """
    message = input('Введите сообщение для отправки или \'!!!\' для завершения работы: ')
    if message == '!!!':
        sock.close()
        CLIENT_LOG.info('Завершение работы по команде пользователя.')
        print('Спасибо за использование нашего сервиса!')
        sys.exit(0)
    message_dict = {
        ACTION: MESSAGE,
        TIME: time.time(),
        ACCOUNT_NAME: account_name,
        MESSAGE_TEXT: message
    }
    CLIENT_LOG.debug(f'Сформировали сообщение: {message_dict}')
    return message_dict


@func_to_log
def process_answer(message):
    CLIENT_LOG.debug(f'Обработка сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200:OK'
        else:
            return f'400: {message[ERROR]}'
    CLIENT_LOG.error(f'{ReqFieldMissingError(RESPONSE)}')
    raise ReqFieldMissingError(RESPONSE)


@func_to_log
def message_from_server(message):
    """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
    if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and MESSAGE_TEXT in message:
        print(f'Получено сообщение от пользователя '
              f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
        CLIENT_LOG.info(f'Получено сообщение от пользователя '
                    f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
    else:
        CLIENT_LOG.error(f'Получено некорректное сообщение с сервера: {message}')


def main():
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
    # except ValueError:
    #     # print("value error")
    #     CLIENT_LOG.error("Value error!")
    CLIENT_LOG.info(f'Запущен клиент с парамертами: '
                    f'адрес сервера: {server_address}, порт: {server_port}')
    try:
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect((server_address, server_port))
        msg_to_server = create_presence()
        send_message(client_sock, msg_to_server)
        answer = process_answer(get_message(client_sock))
        # print(answer)
        CLIENT_LOG.info(f"Получен ответ от сервера: {answer}")
    except json.JSONDecodeError:
        CLIENT_LOG.error('Не удалось декодировать полученную Json строку.')
    except ReqFieldMissingError as missing_error:
        CLIENT_LOG.error(f'В ответе сервера отсутствует необходимое поле '
                         f'{missing_error.missing_field}')
    except ConnectionRefusedError:
        CLIENT_LOG.critical(f'Не удалось подключиться к серверу {server_address}:{server_port}, '
                            f'конечный компьютер отверг запрос на подключение.')
    else:
        # Если соединение с сервером установлено корректно,
        # начинаем обмен с ним, согласно требуемому режиму.
        # основной цикл прогрммы:
        client_mode = ''
        if '-m' in sys.argv:
            client_mode = sys.argv[sys.argv.index('-m') + 1]
        if client_mode not in ('listen', 'send'):
            CLIENT_LOG.critical(f'Указан недопустимый режим работы {client_mode}, возможны режимы: listen, send')
            sys.exit(1)
        if client_mode == 'send':
            print(f'Запущен консольный клиент. Режим работы - отправка сообщений.')
        else:
            print('Запущен консольный клиент. Режим работы - приём сообщений.')

        while True:
            # режим работы - отправка сообщений
            if client_mode == 'send':
                try:
                    msg_to_server = create_message(client_sock)
                    send_message(client_sock, msg_to_server)
                except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                    CLIENT_LOG.error(f'Соединение с сервером {server_address} было потеряно.')
                    sys.exit(1)
                    # Режим работы приём:
            if client_mode == 'listen':
                try:
                    message_from_server(get_message(client_sock))
                except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                    CLIENT_LOG.error(f'Соединение с сервером {server_address} было потеряно.')
                    sys.exit(1)


if __name__ == '__main__':
    main()
