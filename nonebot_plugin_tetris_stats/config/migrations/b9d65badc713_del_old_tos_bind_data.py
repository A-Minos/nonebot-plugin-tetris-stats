"""Del old TOS bind data

迁移 ID: b9d65badc713
父迁移: 6c3206f90cc3
创建时间: 2023-12-30 00:27:40.991704

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = 'b9d65badc713'
down_revision: str | Sequence[str] | None = '6c3206f90cc3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = '') -> None:
    if name:
        return

    Base = automap_base()  # noqa: N806
    connection = op.get_bind()
    Base.prepare(autoload_with=connection)

    Bind = Base.classes.nonebot_plugin_tetris_stats_bind  # noqa: N806
    with Session(connection) as session:
        session.query(Bind).filter(Bind.game_platform == 'TOS').delete()
        session.commit()


def downgrade(name: str = '') -> None:
    if name:
        return
