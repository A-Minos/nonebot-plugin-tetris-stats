"""Merge old db

迁移 ID: 9cd1647db502
父迁移: 9866f53ce44f
创建时间: 2023-11-11 16:51:30.718277

"""

from __future__ import annotations

from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING

from alembic import op
from nonebot import get_driver
from nonebot.log import logger
from sqlalchemy import Connection, create_engine, inspect, text
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = '9cd1647db502'
down_revision: str | Sequence[str] | None = '9866f53ce44f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

driver = get_driver()
config = driver.config


def migrate_old_data(connection: Connection) -> None:
    Base = automap_base()  # noqa: N806
    Base.prepare(autoload_with=op.get_bind())
    Bind = Base.classes.nonebot_plugin_tetris_stats_bind  # noqa: N806

    def non_empty(obj: str) -> bool:
        return bool(obj != '' and not obj.isspace())

    def is_int(obj: int | str) -> bool:
        return bool(isinstance(obj, int) or obj.isdigit())

    bind_list = [
        Bind(chat_platform='OneBot V11', chat_account=int(row.QQ), game_platform='IO', game_account=row.USER)
        for row in connection.execute(text('select QQ, USER from IOBIND;'))
        if is_int(row.QQ) and non_empty(row.USER)
    ]
    bind_list.extend(
        [
            Bind(chat_platform='OneBot V11', chat_account=int(row.QQ), game_platform='TOP', game_account=row.USER)
            for row in connection.execute(text('select QQ, USER from TOPBIND;'))
            if is_int(row.QQ) and non_empty(row.USER)
        ]
    )
    with Session(op.get_bind()) as session:
        session.add_all(bind_list)
        session.commit()
    logger.success('nonebot_plugin_tetris_stats: 迁移完成')


def upgrade(name: str = '') -> None:
    if name:
        return
    try:
        db_path = Path(config.db_url)
    except AttributeError:
        db_path = Path('data/nonebot_plugin_tetris_stats/data.db')
    if db_path.exists() is False:
        logger.warning('nonebot_plugin_tetris_stats: 未发现老版本的数据')
        logger.success('nonebot_plugin_tetris_stats: 跳过迁移')
        return
    copyfile(db_path, db_path.parent / 'data.db.bak')
    engine = create_engine(f'sqlite:///{db_path.absolute()!s}')
    with engine.connect() as connection:
        tables = inspect(connection).get_table_names()
        if 'IOBIND' not in tables or 'TOPBIND' not in tables:
            logger.warning('nonebot_plugin_tetris_stats: 未发现老版本的数据')
            logger.success('nonebot_plugin_tetris_stats: 跳过迁移')
            return
        if 'IORANK' not in tables:
            msg = 'nonebot_plugin_tetris_stats: 请先安装 0.4.4 版本完成迁移之后再升级'
            logger.warning(msg)
            raise RuntimeError(msg)
        logger.info('nonebot_plugin_tetris_stats: 发现来自老版本的数据, 正在迁移...')
        migrate_old_data(connection)
    db_path.unlink()


def downgrade(name: str = '') -> None:
    if name:
        return
