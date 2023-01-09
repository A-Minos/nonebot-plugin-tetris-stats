from typing import Any, Awaitable, Callable, Literal

GameType = Literal['IO', 'TOP', 'TOS']
CommandType = Literal['bind', 'query']
AsyncCallable = Callable[..., Awaitable[Any]]
