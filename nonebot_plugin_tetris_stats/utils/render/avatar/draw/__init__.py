from abc import ABC, abstractmethod
from enum import Enum
from random import Random
from typing import Any, ClassVar

from PIL.Image import Image
from typing_extensions import Self


class Piece(Enum):
    Z = (
        (True, True, False),
        (False, True, True),
    )

    S = (
        (False, True, True),
        (True, True, False),
    )

    J = (
        (True, False, False),
        (True, True, True),
    )

    L = (
        (False, False, True),
        (True, True, True),
    )

    T = (
        (False, True, False),
        (True, True, True),
    )

    I = (  # noqa: E741
        (True, True, True, True),
    )

    O = (  # noqa: E741
        (True, True),
        (True, True),
    )

    I5 = (
        (True, True, True, True, True),  # fmt: skip
    )

    V = (
        (True, False, False),
        (True, False, False),
        (True, True, True),
    )

    T5 = (
        (True, True, True),
        (False, True, False),
        (False, True, False),
    )

    U = (
        (True, False, True),
        (True, True, True),
    )

    W = (
        (True, False, False),
        (True, True, False),
        (False, True, True),
    )

    X = (
        (False, True, False),
        (True, True, True),
        (False, True, False),
    )

    J5 = (
        (True, False, False, False),
        (True, True, True, True),
    )

    L5 = (
        (False, False, False, True),
        (True, True, True, True),
    )

    H = (
        (False, False, True, True),
        (True, True, True, False),
    )

    N = (
        (True, True, False, False),
        (False, True, True, True),
    )

    Y = (
        (False, True, False, False),
        (True, True, True, True),
    )

    R = (
        (False, False, True, False),
        (True, True, True, True),
    )

    P = (
        (True, True, False),
        (True, True, True),
    )

    Q = (
        (False, True, True),
        (True, True, True),
    )

    F = (
        (True, False, False),
        (True, True, True),
        (False, True, False),
    )

    E = (
        (False, False, True),
        (True, True, True),
        (False, True, False),
    )

    S5 = (
        (False, True, True),
        (False, True, False),
        (True, True, False),
    )

    Z5 = (
        (True, True, False),
        (False, True, False),
        (False, True, True),
    )


PIECE_MEMBERS = tuple(Piece)


class SkinManager:
    skin: ClassVar[list['Skin']] = []

    @classmethod
    def register(cls, skin: 'Skin') -> None:
        cls.skin.append(skin)

    @classmethod
    def get_skin(cls, send: float | str | bytes | bytearray | None = None) -> 'Skin':
        return Random(send).choice(cls.skin)  # noqa: S311


class Skin(ABC):
    def __new__(cls, *args: Any, **kwargs: Any) -> Self:  # noqa: ANN401, ARG004
        instance = super().__new__(cls)
        SkinManager.register(instance)
        return instance

    @abstractmethod
    def get_piece(self, piece: Piece) -> Image:
        raise NotImplementedError


from . import tech  # noqa: E402, F401
