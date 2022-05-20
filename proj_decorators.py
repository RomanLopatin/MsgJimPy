import sys
import logging
import traceback


def func_to_log(func):
    """Декоратор """
    if 'server.py' in sys.argv[0]:
        CURRENT_LOG = logging.getLogger('app.server')
    else:
        CURRENT_LOG = logging.getLogger('app.client')

    def log_writer(*args, **kwargs):
        """Обертка"""
        res = func(*args, **kwargs)
        print(
            f'my log: {func.__name__}({args}, {kwargs}) = {res}, {sys.argv[0]},{func.__module__},{traceback.format_stack()[0].strip().split()[-1]}')
        CURRENT_LOG.debug(
            f'Вызана функция {func.__name__} c параметрами {args}, {kwargs}'
            f'из функции {traceback.format_stack()[0].strip().split()[-1]} модуля {func.__module__}.'
        )
        return res

    return log_writer
