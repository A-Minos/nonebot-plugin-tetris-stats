"""migrate nonebot_plugin_tetris_stats_tetriohistoricaldata

迁移 ID: bbbdfd94e6fa
父迁移: d61e6ae36586
创建时间: 2025-07-18 00:42:33.730885

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

revision: str = 'bbbdfd94e6fa'
down_revision: str | Sequence[str] | None = 'd61e6ae36586'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def data_migrate() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = insp.get_table_names()
    if 'nonebot_plugin_tetris_stats_tetriohistoricaldata' not in table_names:
        return

    Base = automap_base()  # noqa: N806
    Base.prepare(autoload_with=conn)
    Old = Base.classes.nonebot_plugin_tetris_stats_tetriohistoricaldata  # noqa: N806
    New = Base.classes.nb_t_io_hist_data  # noqa: N806

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
                        user_unique_identifier=i.user_unique_identifier,
                        api_type=i.api_type,
                        data=i.data,
                        update_time=i.update_time,
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
