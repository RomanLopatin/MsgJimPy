import json
from common.variables import MAX_PACKAGE_LENGTH, ENCODING
from common.errors import IncorrectDataRecivedError
from common.proj_decorators import func_to_log


# @func_to_log
def get_message(sock):
    encoded_msg = sock.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_msg, bytes):
        json_response = encoded_msg.decode(ENCODING)
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        else:
            raise IncorrectDataRecivedError
    else:
        raise IncorrectDataRecivedError

@func_to_log
def send_message(sock, message):
    if not isinstance(message, dict):
        raise TypeError
    json_message = json.dumps(message)
    encoded_message = json_message.encode(ENCODING)
    sock.send(encoded_message)
