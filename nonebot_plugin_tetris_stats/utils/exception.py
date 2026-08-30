from tarina.lang.model import LangItem
from typing_extensions import override


class TetrisStatsError(Exception):
    """所有 TetrisStats 发生的异常基类"""

    def __init__(self, message: str | LangItem = '', **format_kwargs: object):
        self._message = message
        self._format_kwargs = format_kwargs

    @property
    def message(self) -> str:
        return self.render()

    def render(self, locale: str | None = None) -> str:
        if isinstance(self._message, LangItem):
            return self._message(locale, **self._format_kwargs)
        if self._format_kwargs:
            return self._message.format(**self._format_kwargs)
        return self._message

    @override
    def __str__(self) -> str:
        return self.render()

    @override
    def __repr__(self) -> str:
        return self.render()


class NeedCatchError(TetrisStatsError):
    """需要被捕获的异常基类"""


class RequestError(NeedCatchError):
    """请求错误"""

    def __init__(
        self,
        message: str | LangItem = '',
        *,
        status_code: int | None = None,
        **format_kwargs: object,
    ):
        if status_code is not None:
            format_kwargs.setdefault('status_code', status_code)
        super().__init__(message, **format_kwargs)
        self.status_code = status_code


class MessageFormatError(NeedCatchError):
    """用户发送的消息格式不正确"""


class RecordNotFoundError(NeedCatchError):
    """找不到用户的某种记录"""


class FallbackError(NeedCatchError):
    """需要回滚至更通用的方法"""


class DoNotCatchError(TetrisStatsError):
    """不应该被捕获的异常基类"""


class WhatTheFuckError(DoNotCatchError):
    """用于表示不应该出现的情况 ("""


class NoFallbackError(DoNotCatchError):  # 暂时没用 但是先写了
    """没有可用的回退方法"""
