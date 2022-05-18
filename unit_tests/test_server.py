import os
import unittest
import sys

sys.path.append(os.path.join(os.getcwd(), '..'))

from server import process_client_message
from common.variables import ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR, TIME


class TestServer(unittest.TestCase):
    """класс юнит-тестов функций сервера (server/process_client_message)"""

    ok_return = {
        RESPONSE: 200
    }

    error_return = {
        RESPONSE: 400,
        ERROR: 'Bad request'
    }

    def test_ok_return(self):
        """тест корректного запроса"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: 20.00, USER: {ACCOUNT_NAME: 'Guest'}}), self.ok_return)

    def test_err_return_wrong_action(self):
        """тест некорректного запроса - неверное действие"""
        self.assertEqual(process_client_message(
            {ACTION: 'WRONG ACTION', TIME: 20.00, USER: {ACCOUNT_NAME: 'Guest'}}), self.error_return)

    def test_err_return_no_action(self):
        """тест некорректного запроса - действие отсутствует"""
        self.assertEqual(process_client_message(
            {TIME: '20.00', USER: {ACCOUNT_NAME: 'Guest'}}), self.error_return)

    def test_err_return_no_time(self):
        """тест некорректного запроса - время отсутствует"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Guest'}}), self.error_return)

    def test_err_return_wrong_user(self):
        """тест некорректного запроса - неверный пользователь"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: 20.00, USER: {ACCOUNT_NAME: 'wrong_user'}}), self.error_return)

    def test_err_return_no_user(self):
        """тест некорректного запроса - пользователь отсутствует"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: '20.00'}), self.error_return)
    #


if __name__ == '__main__':
    unittest.main()
