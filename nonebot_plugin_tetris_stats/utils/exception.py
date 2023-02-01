class TetrisStatsError(Exception):
    """所有 TetrisStats 发生的异常基类"""

    def __init__(self, message: str | None = None):
        self.message = message

    def __str__(self):
        return self.message


class NeedCatchError(TetrisStatsError):
    """需要被捕获的异常基类"""


class DoNotCatchError(TetrisStatsError):
    """不应该被捕获的异常基类"""


class RequestError(NeedCatchError):
    """用于表示请求错误"""


class DatabaseVersionError(DoNotCatchError):
    """用于表示数据库版本错误"""


class WhatTheFuckError(DoNotCatchError):
    """用于表示不应该出现的情况 ("""
