import json
import logging
import logs.client_log_config
import socket
import sys
import time
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_PORT, \
    DEFAULT_IP_ADDRESS
from common.utils import get_message, send_message
from errors import ReqFieldMissingError

CLIENT_LOG = logging.getLogger('app.client')


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


def process_answer(message):
    CLIENT_LOG.debug(f'Обработка сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200:OK'
        else:
            return f'400: {message[ERROR]}'
    CLIENT_LOG.error(f'{ReqFieldMissingError(RESPONSE)}')
    raise ReqFieldMissingError(RESPONSE)


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


if __name__ == '__main__':
    main()
