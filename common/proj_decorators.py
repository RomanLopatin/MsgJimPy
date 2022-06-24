import sys
import logging
import traceback


def func_to_log(func):
    """Декоратор """
    if 'server.py' in sys.argv[0]:
        current_log = logging.getLogger('app.server')
    else:
        current_log = logging.getLogger('app.client')

    def log_writer(*args, **kwargs):
        """Обертка"""
        current_log.debug(
            f'Вызываем функцию {func.__name__} c параметрами {args}, {kwargs}'
            f'из функции {traceback.format_stack()[0].strip().split()[-1]} модуля {func.__module__}.'
        )
        res = func(*args, **kwargs)

        return res

    return log_writer
