import os
import unittest
import sys

sys.path.append(os.path.join(os.getcwd(), '..'))

from client import create_presence, process_answer
from server import process_client_message
from common.variables import ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR, TIME
from common.utils import get_message, send_message
from errors import ReqFieldMissingError


class TestClient(unittest.TestCase):
    """класс юнит-тестов функций клиента (client) """
    some_time = 'some time'
    other_account_name = "some_user"

    create_presence_ok_return = {
        ACTION: PRESENCE,
        TIME: some_time,
        USER: {
            ACCOUNT_NAME: 'Guest'
        }
    }

    def test_create_presence_ok_return_no_user(self):
        """тест корректного запроса (create_presence) - пользователь не задан """
        create_presence_fact_return = create_presence()
        create_presence_fact_return[TIME] = self.some_time
        self.assertEqual(create_presence_fact_return, self.create_presence_ok_return)

    def test_create_presence_ok_return_some_user(self):
        """тест корректного запроса (create_presence)  - пользователь задан"""
        some_user = 'some_user'
        create_presence_fact_return = create_presence(some_user)
        create_presence_fact_return[TIME] = self.some_time
        self.create_presence_ok_return[USER][ACCOUNT_NAME] = some_user
        self.assertEqual(create_presence_fact_return, self.create_presence_ok_return)

    def test_process_answer_return_200(self):
        """тест корректного запроса (process_answer/ RESPONSE: 200) - """
        self.assertEqual(process_answer({RESPONSE: 200}), '200:OK')

    def test_process_answer_return_400(self):
        """тест корректного запроса (process_answer/ RESPONSE: 400) - """
        self.assertEqual(process_answer({RESPONSE: 400, ERROR: 'Bad Request'}), '400: Bad Request')

    def test_process_answer_raise_exception(self):
        """тест некорректного запроса (process_answer/Raise ValueError"""
        self.assertRaises(ReqFieldMissingError, process_answer, {ERROR: 'Bad Request'})


if __name__ == '__main__':
    unittest.main()
