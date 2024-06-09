class TetrisStatsError(Exception):
    """所有 TetrisStats 发生的异常基类"""

    def __init__(self, message: str = ''):
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return self.message


class NeedCatchError(TetrisStatsError):
    """需要被捕获的异常基类"""


class RequestError(NeedCatchError):
    """请求错误"""

    def __init__(self, message: str = '', *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class MessageFormatError(NeedCatchError):
    """用户发送的消息格式不正确"""


class DoNotCatchError(TetrisStatsError):
    """不应该被捕获的异常基类"""


class WhatTheFuckError(DoNotCatchError):
    """用于表示不应该出现的情况 ("""
