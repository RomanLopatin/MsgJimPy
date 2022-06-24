import dis
from pprint import pprint


class ServerVerifier(type):
    """
    метакласс ServerVerifier, выполняет базовую проверку класса «Server»:
    отсутствие вызовов connect для сокетов;
    использование сокетов для работы по TCP.
    """

    # Вызывается для создания экземпляра класса, перед вызовом __init__
    def __init__(cls, future_class_name, future_class_parents, clsdict):
        # Список методов, которые используются в функциях класса:
        methods = []  # получаем с помощью 'LOAD_GLOBAL'
        # Обычно методы, обёрнутые декораторами попадают
        # не в 'LOAD_GLOBAL', а в 'LOAD_METHOD'
        methods_2 = []  # получаем с помощью 'LOAD_METHOD'
        # Атрибуты, используемые в функциях классов
        attrs = []  # получаем с помощью 'LOAD_ATTR'
        for func in clsdict:
            try:
                ret = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    print(i)
                    # opname - имя для операции
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            # заполняем список методами, использующимися в функциях класса
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_METHOD':
                        if i.argval not in methods_2:
                            # заполняем список методами, использующимися в функциях класса, обернутые декораторами
                            methods_2.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            # заполняем список атрибутами, использующимися в функциях класса
                            attrs.append(i.argval)
        # Если обнаружено использование недопустимого метода connect, вызываем исключение:
        if 'connect' in methods:
            raise TypeError('Использование метода connect недопустимо в серверном классе')
        # Если сокет не инициализировался константами SOCK_STREAM(TCP) AF_INET(IPv4), тоже исключение.
        if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
            raise TypeError('Некорректная инициализация сокета.')

        super(ServerVerifier, cls).__init__(future_class_name, future_class_parents,
                                            clsdict)


# Метакласс для проверки корректности клиентов:
class ClientVerifier(type):
    """
    метакласс ClientVerifier, выполняет базовую проверку класса «Clien»
    (для некоторых проверок уместно использовать модуль dis):
    отсутствие вызовов accept и listen для сокетов;
    использование сокетов для работы по TCP;
    """

    def __init__(cls, future_class_name, future_class_parents, clsdict):
        # Список методов, которые используются в функциях класса:
        methods = []
        for func in clsdict:
            # Пробуем
            try:
                ret = dis.get_instructions(clsdict[func])
                # Если не функция то ловим исключение
            except TypeError:
                pass
            else:
                # Если функция разбираем код, получая используемые методы.
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
        # Если обнаружено использование недопустимого метода accept, listen, socket бросаем исключение:
        # pprint(methods)
        for command in ('accept', 'listen'):
            if command in methods:
                raise TypeError('В классе обнаружено использование запрещённого метода')
        # Вызов get_message или send_message из utils считаем корректным использованием сокетов
        if 'get_message' in methods or 'send_message' in methods or True:
            pass
        else:
            raise TypeError('Отсутствуют вызовы функций, работающих с сокетами.')
        super().__init__(future_class_name, future_class_parents, clsdict)
