"""Лаунчер"""

import subprocess
from time import sleep


def main():
    process = []

    while True:
        action = input('Выберите действие: q - выход, '
                       's - запустить сервер и клиенты, x - закрыть все окна: ')

        if action == 'q':
            break
        elif action == 's':
            print('Убедитесь, что на сервере зарегистрировано необходимо количество клиентов с паролем i, '
                  'где i - порядковый номер клиента.')
            try:
                client_num = int(input('Введите число клиентов для запуска: '))
            except ValueError:
                client_num = 2

            process.append(subprocess.Popen('python server.py -p 7777 -a 127.0.0.1',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))

            for i in range(client_num):
                sleep(1)
                process.append(subprocess.Popen(f'python client.py 127.0.0.1 7777 -n test_{i + 1}  -p {i + 1}',
                                                creationflags=subprocess.CREATE_NEW_CONSOLE))

        elif action == 'x':
            while process:
                victim = process.pop()
                victim.kill()


if __name__ == '__main__':
    main()
