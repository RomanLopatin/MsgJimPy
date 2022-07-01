import sys
import logging

SERVER_LOG = logging.getLogger('app.server')


class PortDescriptor:

    def __set__(self, instance, value):
        try:
            value = int(value)
        except ValueError:
            SERVER_LOG.error(f"Не верный  тип значения порта: {value}")
            sys.exit(1)
        if value < 1024 or value > 65535:
            SERVER_LOG.error(f"Значение порта {value} Не находится в диапазоне 1025 - 65535.")
            sys.exit(1)
        # Если ошибки нет - добавляем порт к атрибутам экземпляра класса
        instance.__dict__[self.my_attr] = value

    def __set_name__(self, owner, my_attr):
        self.my_attr = my_attr
