import sys
import os
import unittest
import json
from common.variables import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE, ENCODING
from common.utils import get_message, send_message

sys.path.insert(0, os.path.join(os.getcwd(), '..'))


class TestSocket:
    """Тестовый класс для имитации сокета - для проверки корректности методов send() и receive(),
    при создании необходимо задать сообщение(словарь)
    """

    def __init__(self, test_message):
        self.test_message = test_message
        self.encoded_message = None
        self.sent_message = None

    def send(self, sent_message):
        """Тестовый метод отправки, он корректно кодирует сообщение (self.encoded_message),
        а так-же сохраняет результат  работы тестируемой функции send() (message_to_send ->self.sent_message) .
        """
        json_test_message = json.dumps(self.test_message)
        # кодируем сообщение
        self.encoded_message = json_test_message.encode(ENCODING)
        # здесь сохраняем то, что отправлено в сокет тестируемой функцией
        self.sent_message = sent_message

    def recv(self, max_len):
        """Получаем данные из сокета"""
        json_test_message = json.dumps(self.test_message)
        return json_test_message.encode(ENCODING)


class TestSocket_resv_no_coding:
    """Тестовый класс для имитации сокета - для проверки корректности методов send() и receive(),
    при создании необходимо задать сообщение(словарь)
    """

    def __init__(self, test_message):
        self.test_message = test_message

    def recv(self, max_len):
        """Получаем данные из сокета без кодирования!"""
        json_test_message = json.dumps(self.test_message)
        return json_test_message


class TestUtils(unittest.TestCase):
    """класс юнит-тестов функций модуля утилит (common/utils) """
    test_message_to_send = {
        ACTION: PRESENCE,
        TIME: 20.00,
        USER: {
            ACCOUNT_NAME: 'user'
        }
    }
    test_msg_receive_ok = {
        RESPONSE: 200
    }
    test_msg_receive_err = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }
    test_msg_receive_non_dict = 'non_dict_message'

    def test_send_message_ok(self):
        """Тест функции отправки сообщения.
        Создадим тестовый сокет и проверим корректность отправки сообщения
        """
        # создаемэкземпляр тестового сокета
        test_socket = TestSocket(self.test_message_to_send)
        # вызываем тестируемую функцию, результаты сохраняем в тестовом сокете (sent_message)
        send_message(test_socket, self.test_message_to_send)
        # Проверяем корректности кодирования сообщения тестовой функцией
        # (сравниваем результат кодирования функцией send() с тестовым кодированием в иммитации сокета)
        self.assertEqual(test_socket.sent_message, test_socket.encoded_message)

    def test_send_message_error(self):
        """Тест функции отправки - обработка исключения неверного формата сообщения.
        Создаем тестовый сокет и проверяем корректность обработки неверного формата сообщения (TypeError)
        """
        # создаем экземпляр тестового сокета
        test_socket = TestSocket(self.test_message_to_send)
        self.assertRaises(TypeError, send_message, test_socket, "non_dict_message")

    def test_get_message_ok(self):
        """Тест функции приёма сообщения о корректной доставке сообщения."""
        test_sock_ok = TestSocket(self.test_msg_receive_ok)
        # тест корректной расшифровки корректного словаря
        self.assertEqual(get_message(test_sock_ok), self.test_msg_receive_ok)

    def test_get_message_error(self):
        """Тест функции приёма сообщения об ошибке"""
        test_sock_err = TestSocket(self.test_msg_receive_err)
        # тест корректной обработки сообщения об ошибке
        self.assertEqual(get_message(test_sock_err), self.test_msg_receive_err)

    def test_get_message_value_error(self):
        """Тест функции получения - обработка исключения неверного формата сообщения (не словарь).
        Создаем тестовый сокет и проверяем корректность обработки неверного формата сообщения (ValueError)
        """
        # создаем экземпляр тестового сокета
        test_sock_non_dict_msg = TestSocket(self.test_msg_receive_non_dict)
        self.assertRaises(ValueError, get_message, test_sock_non_dict_msg)

    def test_get_message_value_error_no_coding(self):
        """Тест функции получения - обработка исключения неверного формата вх.сообщения (не byte).
        Создаем тестовый сокет (для теста ошиочнго формата) и проверяем корректность обработки неверного формата сообщения (ValueError)
        """
        # создаем экземпляр тестового сокета
        test_sock_non_coding_msg = TestSocket_resv_no_coding(self.test_msg_receive_ok)
        self.assertRaises(ValueError, get_message, test_sock_non_coding_msg)


if __name__ == '__main__':
    unittest.main()
