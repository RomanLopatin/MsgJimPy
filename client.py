import json
import socket
import sys
import time
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_PORT, \
    DEFAULT_IP_ADDRESS
from common.utils import get_message, send_message


def create_presence(account_name='Guest'):
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    return out


def process_answer(message):
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200:OK'
        else:
            return f'400: {message[ERROR]}'
    raise ValueError


def main():
    try:
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        if server_port < 1024 or server_port > 65535:
            raise ValueError
    except IndexError:
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
    except ValueError:
        print("value error")

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect((server_address, server_port))
    msg_to_server = create_presence()
    send_message(client_sock, msg_to_server)
    try:
        answer = process_answer(get_message(client_sock))
        print(answer)
    except (ValueError, json.JSONDecodeError):
        print("Не удалось декодировать сообщение сервера!")


if __name__ == '__main__':
    main()
