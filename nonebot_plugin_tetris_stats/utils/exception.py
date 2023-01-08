class TetrisStatsException(Exception):
    '''所有 TetrisStats 发生的异常基类'''

    def __init__(self, message: str | None = None):
        self.message = message

    def __str__(self):
        return self.message


class NeedCatchException(TetrisStatsException):
    '''需要被捕获的异常基类'''


class DoNotCatchException(TetrisStatsException):
    '''不应该被捕获的异常基类'''


class RequestErrorException(NeedCatchException):
    '''用于表示请求错误'''


class WhatTheFuckException(DoNotCatchException):
    '''用于表示不应该出现的情况（'''
