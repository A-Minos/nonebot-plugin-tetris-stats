import datetime
import os
from asyncio import gather
from sqlite3 import Connection, connect

from nonebot import get_driver
from nonebot.log import logger

from .config import Config

driver = get_driver()

config = Config.parse_obj(get_driver().config)


@driver.on_startup
async def _():
    await DataBase.init_db()


@driver.on_shutdown
async def _():
    await DataBase.close_db()


class DataBase():
    '''数据库交互类'''
    _db: Connection | None = None

    @classmethod
    async def init_db(cls) -> Connection:
        '''初始化数据库'''
        if not os.path.exists(os.path.dirname(config.db_path)):
            os.makedirs(os.path.dirname(config.db_path))
        cls._db = connect(config.db_path)
        cursor = cls._db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS IOBIND
                        (QQ INTEGER NOT NULL,
                        USER TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS TOPBIND
                        (QQ INTEGER NOT NULL,
                        USER TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS IORANK
                        (RANK VARCHAR(2) NOT NULL,
                         TRENDING CHAR(1) NOT NULL,
                         TRLINE FLOAT NOT NULL,
                         PLAYERCOUNT INTEGER NOT NULL,
                         AVGAPM FLOAT NOT NULL,
                         AVGPPS FLOAT NOT NULL,
                         ARGVS FLOAT NOT NULL,
                         DATE TEXT NOT NULL)''')
        cls._db.commit()
        logger.info('数据库初始化完成')
        return cls._db

    @classmethod
    async def query_rank_info_today(cls, rank: str) -> list | None:
        '''查询段位信息'''
        db = await cls._get_db()
        cursor = db.cursor()
        cursor.execute('''SELECT TRENDING, TRLINE, PLAYERCOUNT, AVGAPM, AVGPPS, ARGVS, DATE
                        FROM IORANK
                        WHERE RANK = ? AND DATE = ?''', (rank, datetime.date.today()))
        result = cursor.fetchone()

        if result is None:
            return None

        return list(result)

    @classmethod
    async def write_rank_info_today(cls, rank: str, trline: int, playercount: int, avgapm: float, avgpps: float, avgvs: float):
        '''写入段位信息'''

        db = await cls._get_db()
        cursor = db.cursor()
        cursor.execute('''SELECT TRLINE
                        FROM IORANK
                        WHERE RANK = ? AND DATE = ?''', (rank, datetime.date.today() - datetime.timedelta(days=1)))

        result = cursor.fetchone()

        if result is None:
            trending = '?'
        elif trline > result[0]:
            trending = '↑'
        elif trline == result[0]:
            trending = '-'
        elif trline < result[0]:
            trending = '↓'

        cursor.execute('''INSERT INTO IORANK
                        (RANK, TRENDING, TRLINE, PLAYERCOUNT, AVGAPM, AVGPPS, ARGVS, DATE)
                        VALUES (?,?,?,?,?,?,?,?)''',
                       (rank, trending, trline, playercount, avgapm, avgpps, avgvs, datetime.date.today()))

        db.commit()

    @classmethod
    async def _get_db(cls) -> Connection:
        '''获取数据库对象'''
        return cls._db or await cls.init_db()

    @classmethod
    async def query_bind_info(cls, qq_number: str | int, game_type: str) -> str | None:
        '''查询绑定信息'''
        db = await cls._get_db()
        cursor = db.cursor()
        cursor.execute(
            f'SELECT USER FROM {game_type}BIND WHERE QQ = {qq_number}')
        user = cursor.fetchone()
        if user is None:
            return None
        return user[0]

    @classmethod
    async def write_bind_info(cls, qq_number: str | int, user: str, game_type: str) -> str:
        '''写入绑定信息'''
        bind_info, db = await gather(
            cls.query_bind_info(qq_number=qq_number, game_type=game_type),
            cls._get_db()
        )
        cursor = db.cursor()
        if bind_info is not None:
            cursor.execute(
                f'UPDATE {game_type}BIND SET USER = ? WHERE QQ = ?', (user, qq_number))
            message = '更新成功'
        elif bind_info is None:
            cursor.execute(
                f'INSERT INTO {game_type}BIND (QQ, USER) VALUES (?, ?)', (qq_number, user))
            message = '绑定成功'
        else:
            raise ValueError('预期外行为, 请上报GitHub')
        db.commit()
        return message

    @classmethod
    async def close_db(cls) -> None:
        '''关闭数据库对象'''
        if isinstance(cls._db, Connection):
            cls._db.close()
