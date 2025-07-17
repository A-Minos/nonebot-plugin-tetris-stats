"""migrate nonebot_plugin_tetris_stats_triggerhistoricaldatav2

迁移 ID: bc6abd57928f
父迁移: ee76ae37d70a
创建时间: 2025-07-18 04:33:04.222045

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
from nonebot.log import logger
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from sqlalchemy import inspect
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = 'bc6abd57928f'
down_revision: str | Sequence[str] | None = 'ee76ae37d70a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def data_migrate() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = insp.get_table_names()
    if 'nonebot_plugin_tetris_stats_triggerhistoricaldatav2' not in table_names:
        return

    Base = automap_base()  # noqa: N806
    Base.prepare(autoload_with=conn)
    Old = Base.classes.nonebot_plugin_tetris_stats_triggerhistoricaldatav2  # noqa: N806
    New = Base.classes.nb_t_trigger_hist_v2  # noqa: N806

    with Session(conn) as db_session:
        count = db_session.query(Old).count()
        if count == 0:
            return

        logger.warning('tetris_stats: 正在迁移数据, 请不要关闭程序...')

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task('迁移数据...', total=count)

            for i in db_session.query(Old).yield_per(1):
                db_session.add(
                    New(
                        id=i.id,
                        trigger_time=i.trigger_time,
                        session_persist_id=i.session_persist_id,
                        game_platform=i.game_platform,
                        command_type=i.command_type,
                        command_args=i.command_args,
                        finish_time=i.finish_time,
                    )
                )

                progress.update(task, advance=1)

                if progress.tasks[task].completed % 100 == 0:
                    db_session.commit()

        db_session.commit()

        logger.success('tetris_stats: 数据迁移完成!')


def upgrade(name: str = '') -> None:
    if name:
        return
    data_migrate()


def downgrade(name: str = '') -> None:
    if name:
        return
