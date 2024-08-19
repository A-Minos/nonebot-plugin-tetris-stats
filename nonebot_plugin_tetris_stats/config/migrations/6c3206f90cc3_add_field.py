"""Add redundant platform field

迁移 ID: 6c3206f90cc3
父迁移: 9f6582279ce2
创建时间: 2023-11-26 20:15:56.033892

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = '6c3206f90cc3'
down_revision: str | Sequence[str] | None = '9f6582279ce2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = '') -> None:
    if name:
        return
    from json import dumps, loads

    Base = automap_base()  # noqa: N806
    connection = op.get_bind()
    Base.prepare(autoload_with=connection)

    HistoricalData = Base.classes.nonebot_plugin_tetris_stats_historicaldata  # noqa: N806

    with Session(connection) as session:
        for row in session.query(HistoricalData):
            platform = row.game_platform
            game_user = loads(row.game_user)
            processed_data = loads(row.processed_data)
            game_user['platform'] = platform
            processed_data['platform'] = platform
            row.game_user = dumps(game_user)
            row.processed_data = dumps(processed_data)
            session.add(row)
        session.commit()


def downgrade(name: str = '') -> None:
    if name:
        return
    from json import dumps, loads

    Base = automap_base()  # noqa: N806
    connection = op.get_bind()
    Base.prepare(autoload_with=connection)

    HistoricalData = Base.classes.nonebot_plugin_tetris_stats_historicaldata  # noqa: N806

    with Session(connection) as session:
        for row in session.query(HistoricalData):
            game_user = loads(row.game_user)
            processed_data = loads(row.processed_data)
            game_user.pop('platform', None)
            processed_data.pop('platform', None)
            row.game_user = dumps(game_user)
            row.processed_data = dumps(processed_data)
            session.add(row)
        session.commit()
