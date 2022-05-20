import json
import socket
from common.variables import MAX_PACKAGE_LENGTH, ENCODING
from proj_decorators import func_to_log


@func_to_log
def get_message(sock):
    encoded_msg = sock.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_msg, bytes):
        json_msg = encoded_msg.decode(ENCODING)
        if isinstance(json_msg, str):
            dict_msg = json.loads(json_msg)
            if isinstance(dict_msg, dict):
                return dict_msg
            raise ValueError
        raise ValueError
    raise ValueError


@func_to_log
def send_message(sock, message):
    if not isinstance(message, dict):
        raise TypeError
    json_message = json.dumps(message)
    encoded_message = json_message.encode(ENCODING)
    sock.send(encoded_message)
