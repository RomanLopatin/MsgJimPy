"""Лаунчер"""

import subprocess

PROCESS = []

while True:
    ACTION = input('Выберите действие: q - выход, '
                   's - запустить сервер и клиенты, x - закрыть все окна: ')

    if ACTION == 'q':
        break
    elif ACTION == 's':
        PROCESS.append(subprocess.Popen('python server.py',
                                        creationflags=subprocess.CREATE_NEW_CONSOLE))
        # for i in range(2):
        #     PROCESS.append(subprocess.Popen('python client.py',
        #                                     creationflags=subprocess.CREATE_NEW_CONSOLE))

        for i in range(2):
            PROCESS.append(subprocess.Popen('python client.py 127.0.0.1 7777 -m send',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))
        for i in range(3):
            PROCESS.append(subprocess.Popen('python client.py 127.0.0.1 7777 -m listen',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif ACTION == 'x':
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
