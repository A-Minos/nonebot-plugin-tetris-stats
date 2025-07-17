"""migrate nonebot_plugin_tetris_stats_bind

迁移 ID: d61e6ae36586
父迁移: b2075a5ce371
创建时间: 2025-07-17 23:58:13.408384

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
from nonebot.log import logger
from objprint import objprint
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from sqlalchemy import inspect
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = 'd61e6ae36586'
down_revision: str | Sequence[str] | None = 'b2075a5ce371'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def data_migrate() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = insp.get_table_names()
    if 'nonebot_plugin_tetris_stats_bind' not in table_names:
        return

    Base = automap_base()  # noqa: N806
    Base.prepare(autoload_with=conn)
    Old = Base.classes.nonebot_plugin_tetris_stats_bind  # noqa: N806
    New = Base.classes.nb_t_bind  # noqa: N806

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

            for i in db_session.query(Old).yield_per(100):
                db_session.add(
                    New(
                        id=i.id,
                        user_id=i.user_id,
                        game_platform=i.game_platform,
                        game_account=i.game_account,
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
