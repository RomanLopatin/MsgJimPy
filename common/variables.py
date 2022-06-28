DEFAULT_PORT = 7777
DEFAULT_IP_ADDRESS = '127.0.0.1'
MAX_CONNECTIONS = 10
MAX_PACKAGE_LENGTH = 1024
ENCODING = 'utf-8'
# Протокол JIM, осн. ключи
ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'account_name'
# Доп. ключи
PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
MESSAGE = 'message'
MESSAGE_TEXT = 'mess_text'
SENDER = 'sender'
MESSAGE_RECEIVER = 'message_receiver'
EXIT = 'exit'
GET_CONTACTS = 'get_contacts'
LIST_INFO = 'data_list'
REMOVE_CONTACT = 'remove'
ADD_CONTACT = 'add'
USERS_REQUEST = 'get_users'
DATA = 'bin'
PUBLIC_KEY = 'pubkey'
# Словари - ответы:
# 200
RESPONSE_200 = {RESPONSE: 200}
# 202
RESPONSE_202 = {RESPONSE: 202,
                LIST_INFO:None
                }
# 400
RESPONSE_400 = {
            RESPONSE: 400,
            ERROR: None
        }
# 205
RESPONSE_205 = {
    RESPONSE: 205
}

# 511
RESPONSE_511 = {
    RESPONSE: 511,
    DATA: None
}


SERVER_DB = 'sqlite:///server_db.db3'
