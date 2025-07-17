"""Migrate to uninfo

迁移 ID: 766cc7e75a62
父迁移: 612d8b00d9ac
创建时间: 2025-05-26 04:51:54.665200

"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from alembic import op
from nonebot.log import logger
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from sqlalchemy import inspect
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = '766cc7e75a62'
down_revision: str | Sequence[str] | None = '612d8b00d9ac'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def data_migrate() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = insp.get_table_names()
    if 'nonebot_plugin_tetris_stats_triggerhistoricaldata' not in table_names:
        return

    Base = automap_base()  # noqa: N806
    Base.prepare(autoload_with=conn)
    TriggerHistoricalData = Base.classes.nonebot_plugin_tetris_stats_triggerhistoricaldata  # noqa: N806
    TriggerHistoricalDataV2 = Base.classes.nonebot_plugin_tetris_stats_triggerhistoricaldatav2  # noqa: N806

    with Session(conn) as db_session:
        count = db_session.query(TriggerHistoricalData).count()
        if count == 0:
            return

        try:
            from nonebot_session_to_uninfo import check_tables, get_id_map  # type: ignore[import-untyped]
        except ImportError as err:
            msg = '请安装 `nonebot-session-to-uninfo` 以迁移数据'
            raise ValueError(msg) from err

        check_tables()

        migration_limit = 10000  # 每次迁移的数据量为 10000 条
        last_id = -1
        id_map: dict[int, int] = {}

        logger.warning('tetris_stats: 正在迁移数据, 请不要关闭程序...')

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task('迁移数据...', total=count)

            for _ in range(math.ceil(count / migration_limit)):
                records = (
                    db_session.query(TriggerHistoricalData)
                    .order_by(TriggerHistoricalData.id)
                    .where(TriggerHistoricalData.id > last_id)
                    .limit(migration_limit)
                    .all()
                )
                last_id = records[-1].id

                session_ids = [
                    record.session_persist_id for record in records if record.session_persist_id not in id_map
                ]
                if session_ids:
                    id_map.update(get_id_map(session_ids))

                db_session.add_all(
                    TriggerHistoricalDataV2(
                        id=record.id,
                        session_persist_id=id_map[record.session_persist_id],
                        trigger_time=record.trigger_time,
                        game_platform=record.game_platform,
                        command_type=record.command_type,
                        command_args=record.command_args,
                        finish_time=record.finish_time,
                    )
                    for record in records
                )

                progress.update(task, advance=len(records))

        db_session.commit()

        logger.success('tetris_stats: 数据迁移完成!')


def upgrade(name: str = '') -> None:
    if name:
        return
    if op.get_bind().dialect.name == 'postgresql':
        return
    data_migrate()


def downgrade(name: str = '') -> None:
    if name:
        return
    if op.get_bind().dialect.name == 'postgresql':
        return
