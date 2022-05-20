import json
import logging
import logs.server_log_config
import socket
import sys
import time
from common.variables import ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR, \
    DEFAULT_PORT, MAX_CONNECTIONS, TIME

from common.utils import get_message, send_message
from errors import IncorrectDataRecivedError
from proj_decorators import func_to_log

SERVER_LOG = logging.getLogger('app.server')


@func_to_log
def process_client_message(message):
    SERVER_LOG.debug(f'Вызов ф-ии process_client_message(). Разбор сообщения от клиента : {message}')
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message and message[USER][ACCOUNT_NAME] == 'Guest':
        return {RESPONSE: 200}
    return {
        RESPONSE: 400,
        ERROR: 'Bad request'
    }


def main():
    """
    Сперва пытаемся обработать параметры командной строки (address_to_listen и port_to_listen).
    Если не удается - используем значения по умолчанию
    server.py -p 8888 -a 127.0.0.1
    """
    try:
        if '-p' in sys.argv:
            port_to_listen = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            port_to_listen = DEFAULT_PORT
        if port_to_listen < 1024 or port_to_listen > 65535:
            raise ValueError
    except IndexError:
        # print("Index error (port value should be defined!)")
        SERVER_LOG.error('Index error (port value should be defined!)')
        sys.exit(1)
    except ValueError:
        # print("Value error (port value should be in range 1024-65535!)")
        SERVER_LOG.error('Value error (port value should be in range 1024-65535!)')
        sys.exit(1)

    try:
        if '-a' in sys.argv:
            address_to_listen = sys.argv[sys.argv.index('-a') + 1]
        else:
            address_to_listen = ''
    except IndexError:
        # print("Index error (address)")
        SERVER_LOG.error('Index error (address)')
        sys.exit(1)

    # Инициализация сокета и обмен
    serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serv_sock.bind(('', port_to_listen))
    serv_sock.listen(MAX_CONNECTIONS)

    while True:
        client_sock, client_address = serv_sock.accept()
        SERVER_LOG.info(f'Установили соедение с клиентом по адресу: {client_address}')
        try:
            message_from_client = get_message(client_sock)
            # print(message_from_client)
            SERVER_LOG.debug(f'Получено сообщение от клиента: {message_from_client}')
            response = process_client_message(message_from_client)
            SERVER_LOG.debug(f'Сформирован ответ клиенту: {response}')
            send_message(client_sock, response)
            client_sock.close()
            SERVER_LOG.debug(f'Закрыли соединение с клиентом ({client_address}).')
        except json.JSONDecodeError:
            SERVER_LOG.error(f'Не удалось декодировать JSON строку, полученную от '
                             f'клиента {client_address} ({message_from_client})')
            client_sock.close()
        except IncorrectDataRecivedError:
            SERVER_LOG.error(f'От клиента {client_address} приняты некорректные данные.'
                             f'Соединение закрывается.')
            client_sock.close()
        except ValueError:
            SERVER_LOG.error(f'Некорр. сообщение (ValueError) от клиента  {client_address}! ({message_from_client})')
            client_sock.close()


if __name__ == '__main__':
    main()
