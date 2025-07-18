"""Add user_unique_identifier field to HistoricalData

迁移 ID: b7fbdafc339a
父迁移: 8a91210ce14d
创建时间: 2024-05-07 16:55:29.527215

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from nonebot.log import logger

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = 'b7fbdafc339a'
down_revision: str | Sequence[str] | None = '8a91210ce14d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = '') -> None:  # noqa: C901
    if name:
        return
    if op.get_bind().dialect.name == 'postgresql':
        return

    from nonebot.compat import type_validate_json  # noqa: PLC0415
    from pydantic import ValidationError  # noqa: PLC0415
    from rich.progress import (  # noqa: PLC0415
        BarColumn,
        MofNCompleteColumn,
        Progress,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
    )
    from sqlalchemy import select  # noqa: PLC0415
    from sqlalchemy.ext.automap import automap_base  # noqa: PLC0415
    from sqlalchemy.orm import Session  # noqa: PLC0415

    with op.batch_alter_table('nonebot_plugin_tetris_stats_historicaldata', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_unique_identifier', sa.String(length=32), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_nonebot_plugin_tetris_stats_historicaldata_user_unique_identifier'),
            ['user_unique_identifier'],
            unique=False,
        )
    Base = automap_base()  # noqa: N806
    connection = op.get_bind()
    Base.prepare(autoload_with=connection)
    HistoricalData = Base.classes.nonebot_plugin_tetris_stats_historicaldata  # noqa: N806

    with Session(op.get_bind()) as session:
        count = session.query(HistoricalData).count()
        if count == 0:
            logger.info('空表, 跳过')
        else:
            from nonebot_plugin_tetris_stats.version import __version__  # noqa: PLC0415

            if __version__ != '1.0.4':
                msg = '本迁移需要1.0.4版本, 请先锁定版本至1.0.4版本再执行本迁移'
                logger.critical(msg)
                raise RuntimeError(msg)
            from nonebot_plugin_tetris_stats.game_data_processor.schemas import (  # type: ignore[import-untyped] # noqa: PLC0415
                BaseUser,
            )

            models: list[type[BaseUser]] = BaseUser.__subclasses__()

            def json_to_model(value: str) -> BaseUser:
                for i in models:
                    try:
                        return type_validate_json(i, value)
                    except ValidationError:  # noqa: PERF203
                        ...
                raise ValueError

            with Progress(
                TextColumn('[progress.description]{task.description}'),
                BarColumn(),
                MofNCompleteColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
            ) as progress:
                task_id = progress.add_task('[cyan]Updateing:', total=count)
                for i in range(0, count, 100):
                    for j in session.scalars(
                        select(HistoricalData).where(HistoricalData.id > i).order_by(HistoricalData.id).limit(100)
                    ):
                        model = json_to_model(j.game_user)
                        try:
                            j.user_unique_identifier = model.unique_identifier
                        except ValueError:
                            session.delete(j)
                        progress.update(task_id, advance=1)
                    session.commit()
    with op.batch_alter_table('nonebot_plugin_tetris_stats_historicaldata', schema=None) as batch_op:
        batch_op.alter_column('user_unique_identifier', existing_type=sa.VARCHAR(length=32), nullable=False)
    logger.success('database upgrade success')


def downgrade(name: str = '') -> None:
    if name:
        return
    if op.get_bind().dialect.name == 'postgresql':
        return
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('nonebot_plugin_tetris_stats_historicaldata', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_nonebot_plugin_tetris_stats_historicaldata_user_unique_identifier'))
        batch_op.drop_column('user_unique_identifier')

    # ### end Alembic commands ###
