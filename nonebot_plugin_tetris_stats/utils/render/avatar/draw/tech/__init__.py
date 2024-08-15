from enum import Enum
from pathlib import Path

from nonebot import get_driver
from PIL import Image
from PIL.Image import Resampling
from typing_extensions import override

from .. import Piece, Skin

SINGLE = 30

driver = get_driver()


class Block(Enum):
    Z = (0, 0, 30, 30)
    Y = (30, 0, 60, 30)
    L = (60, 0, 90, 30)
    O = (90, 0, 120, 30)  # noqa: E741
    U = (120, 0, 150, 30)
    Q = (150, 0, 180, 30)
    S = (180, 0, 210, 30)
    H = (210, 0, 240, 30)
    I = (0, 30, 30, 60)  # noqa: E741
    F = (30, 30, 60, 60)
    J = (60, 30, 90, 60)
    R = (90, 30, 120, 60)
    C = (120, 30, 150, 60)
    T = (150, 30, 180, 60)
    W = (180, 30, 210, 60)
    N = (210, 30, 240, 60)


piece_block_mapping = {
    Piece.Z: Block.Z,
    Piece.S: Block.S,
    Piece.J: Block.J,
    Piece.L: Block.L,
    Piece.T: Block.T,
    Piece.I: Block.I,
    Piece.O: Block.O,
    Piece.I5: Block.O,
    Piece.V: Block.I,
    Piece.T5: Block.C,
    Piece.U: Block.U,
    Piece.W: Block.W,
    Piece.X: Block.O,
    Piece.J5: Block.J,
    Piece.L5: Block.L,
    Piece.H: Block.H,
    Piece.N: Block.N,
    Piece.R: Block.R,
    Piece.Y: Block.Y,
    Piece.P: Block.Y,
    Piece.Q: Block.Q,
    Piece.F: Block.F,
    Piece.E: Block.Y,
    Piece.S5: Block.S,
    Piece.Z5: Block.Z,
}


class TechSkin(Skin):
    def __init__(self, path: Path, name: str | None = None) -> None:
        self.path = path
        self.name = name or path.name
        self.image = Image.open(path)
        self._block_cache: dict[Block, Image.Image] = {}

    def get_block(self, block: Block) -> Image.Image:
        return self._block_cache.setdefault(block, self.image.crop(block.value))

    def draw_piece(self, block: Block, piece: Piece, scale: int = 10) -> Image.Image:
        canvas = Image.new(
            'RGBA', (len(piece.value[0]) * SINGLE * scale, len(piece.value) * SINGLE * scale), (0, 0, 0, 0)
        )
        block_img = self.get_block(block).resize((SINGLE * scale, SINGLE * scale), resample=Resampling.BICUBIC)
        for i, row in enumerate(piece.value):
            for j, mino in enumerate(row):
                if mino:
                    canvas.paste(block_img, (j * SINGLE * scale, i * SINGLE * scale))
        return canvas

    @override
    def get_piece(self, piece: Piece) -> Image.Image:
        return self.draw_piece(piece_block_mapping[piece], piece)


@driver.on_startup
def _():
    path = Path(__file__).parent / 'skins'
    for i in sorted(path.iterdir()):
        TechSkin(i)
