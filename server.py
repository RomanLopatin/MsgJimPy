import json
import logging
from select import select

import logs.server_log_config
import socket
import sys
import time
from common.variables import ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR, \
    DEFAULT_PORT, MAX_CONNECTIONS, TIME, MESSAGE_TEXT, MESSAGE, SENDER

from common.utils import get_message, send_message
from errors import IncorrectDataRecivedError
from proj_decorators import func_to_log

SERVER_LOG = logging.getLogger('app.server')


@func_to_log
def process_client_message(message, messages_list, client):
    SERVER_LOG.debug(f'Вызов ф-ии process_client_message(). Разбор сообщения от клиента : {message}')
    # Если это сообщение о присутствии (PRESENCE), принимаем его и отвечаем
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message and message[USER][ACCOUNT_NAME] == 'Guest':
        msg = {RESPONSE: 200}
        send_message(client, msg)
        return
        # Если это сообщение (MESSAGE), то добавляем его в список сообщений.
    elif ACTION in message and message[ACTION] == MESSAGE and \
            TIME in message and MESSAGE_TEXT in message:
        messages_list.append((message[ACCOUNT_NAME], message[MESSAGE_TEXT]))
        return
    else:
        msg = {
            RESPONSE: 400,
            ERROR: 'Bad request'
        }
        send_message(msg, client)
        return


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

    msg_for_log =  f'Запущен сервер, порт для подключений: {port_to_listen}, ' \
                   f'адрес с которого принимаются подключения: {address_to_listen}.'

    SERVER_LOG.info(msg_for_log)
    print(msg_for_log)

    # Инициализация пустого списка клиентов
    all_client_socks = []
    messages = []

    # Инициализация сокета и обмен
    serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serv_sock.bind((address_to_listen, port_to_listen))
    serv_sock.listen(MAX_CONNECTIONS)
    serv_sock.settimeout(1)

    while True:
        try:
            client_sock, client_address = serv_sock.accept()
            SERVER_LOG.info(f'Установили соедение с клиентом по адресу: {client_address}')
        except OSError as err:
            pass
        else:
            print(f"Получен запрос на соединение от {str(client_address)}")
            # ToDo: Добавить запись в лог
            all_client_socks.append(client_sock)
        finally:
            wait = 0
            client_socks_to_read = []
            client_socks_to_write = []
            try:
                if all_client_socks:
                    client_socks_to_read, client_socks_to_write, errors = select(all_client_socks, all_client_socks, [],
                                                                                 wait)
                    print(client_socks_to_read)
                    print(client_socks_to_write)
            except Exception as e:
                print(e)
            # ниже - старый код
            # client_sock, client_address = serv_sock.accept()
            # SERVER_LOG.info(f'Установили соедение с клиентом по адресу: {client_address}')
            if client_socks_to_read:
                for client_sock_to_read in client_socks_to_read:
                    message_from_client = ''
                    try:
                        message_from_client = get_message(client_sock_to_read)
                        print(message_from_client)
                        SERVER_LOG.debug(f'Получено сообщение от клиента: {message_from_client}')
                        process_client_message(message_from_client, messages, client_sock_to_read)
                        # response = process_client_message(message_from_client)
                        # SERVER_LOG.debug(f'Сформирован ответ клиенту: {response}')
                        # send_message(client_sock, response)
                        # client_sock.close()
                        # SERVER_LOG.debug(f'Закрыли соединение с клиентом ({client_address}).')
                    except json.JSONDecodeError:
                        SERVER_LOG.error(f'Не удалось декодировать JSON строку, полученную от '
                                         f'клиента {client_sock_to_read.getpeername()} ({message_from_client})')
                        client_sock_to_read.close()
                        all_client_socks.remove(client_sock_to_read)
                    except IncorrectDataRecivedError:
                        SERVER_LOG.error(f'От клиента {client_sock_to_read.getpeername()} приняты некорректные данные.'
                                         f'Соединение закрывается.')
                        client_sock_to_read.close()
                        all_client_socks.remove(client_sock_to_read)
                    except ValueError:
                        SERVER_LOG.error(
                            f'Некорр. сообщение (ValueError) от клиента  {client_sock_to_read.getpeername()} ({message_from_client})')
                        client_sock_to_read.close()
                        all_client_socks.remove(client_sock_to_read)

            # Если есть сообщения для отправки и ожидающие клиенты, отправляем им сообщение.
            if messages and client_socks_to_write:
                message = {
                    ACTION: MESSAGE,
                    SENDER: messages[0][0],
                    TIME: time.time(),
                    MESSAGE_TEXT: messages[0][1]
                }
                del messages[0]
                for client_sock_to_write in client_socks_to_write:
                    try:
                        send_message(client_sock_to_write, message)
                    except:
                        SERVER_LOG.info(f'Клиент {client_sock_to_write.getpeername()} отключился от сервера.')
                        client_sock_to_write.close()
                        all_client_socks.remove(client_sock_to_write)

if __name__ == '__main__':
    main()
