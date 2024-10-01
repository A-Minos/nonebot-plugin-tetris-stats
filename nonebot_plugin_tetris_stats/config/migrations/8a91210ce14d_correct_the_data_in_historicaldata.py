"""Correct the data in HistoricalData

迁移 ID: 8a91210ce14d
父迁移: 0d50142b780f
创建时间: 2024-05-06 08:16:38.487214

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
from nonebot.log import logger
from sqlalchemy import select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = '8a91210ce14d'
down_revision: str | Sequence[str] | None = '0d50142b780f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = '') -> None:  # noqa: C901
    if name:
        return

    from nonebot.compat import PYDANTIC_V2, type_validate_json
    from pydantic import BaseModel, ValidationError
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
    )

    Base = automap_base()  # noqa: N806
    Base.prepare(autoload_with=op.get_bind())
    HistoricalData = Base.classes.nonebot_plugin_tetris_stats_historicaldata  # noqa: N806
    if PYDANTIC_V2:

        def model_to_json(value: BaseModel) -> str:
            return value.model_dump_json(by_alias=True)
    else:

        def model_to_json(value: BaseModel) -> str:
            return value.json(by_alias=True)

    with Session(op.get_bind()) as session:
        count = session.query(HistoricalData).count()
        if count == 0:
            logger.info('空表, 跳过')
            return

        from nonebot_plugin_tetris_stats.version import __version__

        if __version__ != '1.0.3':
            msg = '本迁移需要1.0.3版本, 请先锁定版本至1.0.3版本再执行本迁移'
            logger.critical(msg)
            raise RuntimeError(msg)

        from nonebot_plugin_tetris_stats.game_data_processor.schemas import (  # type: ignore[import-untyped]
            BaseProcessedData,
        )

        models = BaseProcessedData.__subclasses__()

        def json_to_model(value: str) -> BaseModel:
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
                    model = json_to_model(j.processed_data)
                    j.processed_data = model_to_json(model)
                    progress.update(task_id, advance=1)
                session.commit()
    logger.success('Corrected HistoricalData')


def downgrade(name: str = '') -> None:
    if name:
        return
