from pathlib import Path
from shutil import copyfile
from typing import Any

from nonebot import get_driver
from nonebot.log import logger
from tortoise import Tortoise
from tortoise.connection import connections

from ..utils.config import Config
from ..utils.exception import DatabaseVersionError, WhatTheFuckError
from ..utils.typing import GameType
from ..version import __version__
from .models import Bind, Historical_Data, Version

driver = get_driver()


config = Config.parse_obj(get_driver().config)


@driver.on_startup
async def _():
    await DataBase.init_db()


@driver.on_shutdown
async def _():
    await connections.close_all()


class DataBase:
    '''数据库交互类'''

    db_type: str | None = None

    @classmethod
    async def init_db(cls) -> None:
        '''初始化数据库'''
        logger.debug('开始初始化数据库')
        if config.db_url.startswith('sqlite://'):
            logger.debug('检测到 sqlite 数据库, 进行路径校验')
            cls.db_type = 'sqlite'
            db_dir = Path(config.db_url.strip('sqlite://')).parent
            if not db_dir.exists():
                db_dir.mkdir(parents=True)
            elif not db_dir.is_dir():
                db_dir.unlink()
                db_dir.mkdir(parents=True)
        from . import models

        await Tortoise.init(
            db_url=config.db_url,
            modules={"models": [models]},
            timezone='Asia/Shanghai',
        )
        await Tortoise.generate_schemas()
        await cls.check_and_update_db()
        logger.debug('数据库初始化完成')

    @classmethod
    async def migrate(cls) -> None:
        conn = connections.get('default')
        table = [
            i['name']
            for i in await conn.execute_query_dict(
                'SELECT name FROM sqlite_master WHERE type="table";'
            )
        ]
        if {'IOBIND', 'TOPBIND'}.issubset(table):
            logger.debug('开始迁移数据库')
            if cls.db_type == 'sqlite':
                copyfile(
                    p := Path(config.db_url.strip('sqlite://')),
                    p.with_name('backup.db'),
                )
                logger.debug('数据库备份完成')
            else:
                raise WhatTheFuckError('为什么会有别的类型的数据库需要迁移')
            old_io = await conn.execute_query_dict('select * from IOBIND;')
            old_top = await conn.execute_query_dict('select * from TOPBIND;')
            new_bind = {
                str(i['QQ']): {'IO': None, 'TOP': None} for i in old_io + old_top
            }
            for i in old_io:
                new_bind[str(i['QQ'])].update(IO=i['USER'])
            for i in old_top:
                new_bind[str(i['QQ'])].update(TOP=i['USER'])
            del new_bind['']
            await Bind.bulk_create(
                [Bind(qq=i, IO=j['IO'], TOP=j['TOP']) for i, j in new_bind.items()]
            )
            await conn.execute_script('DROP TABLE IOBIND;')
            await conn.execute_script('DROP TABLE TOPBIND;')
            logger.debug('数据库迁移完成')
        else:
            logger.debug('未识别到旧版数据库')

    @classmethod
    async def check_and_update_db(cls) -> None:
        logger.debug('开始检查数据库版本')
        if (v := await Version.filter()) == []:
            logger.debug('未找到版本信息, 尝试从旧版本迁移')
            await cls.migrate()
            await Version.create(version=__version__)
            v = await Version.filter()
        elif len(v) > 1:
            raise DatabaseVersionError('发现多个版本信息')
        if v[0].version != __version__:
            await Version.filter().update(version=__version__)

    @classmethod
    async def query_bind_info(
        cls, user_ids: dict[str, Any], game_type: GameType
    ) -> str | None:
        '''查询绑定信息'''
        result = await Bind.get_or_none(**user_ids)
        if result is not None:
            loc = locals().copy()
            exec(f'player_id = result.{game_type}', globals(), loc)
            return loc['player_id']
        return None

    @classmethod
    async def write_bind_info(
        cls, user_ids: dict[str, Any], player_ids: dict[GameType, Any]
    ) -> str:
        '''写入绑定信息'''
        await Bind.update_or_create(defaults=player_ids, **user_ids)
        return '绑定成功'

    @classmethod
    async def write_historical(cls, **kwargs) -> None:
        await Historical_Data.create(**kwargs)

    @classmethod
    async def query_historical(cls) -> None:
        # TODO
        ...
