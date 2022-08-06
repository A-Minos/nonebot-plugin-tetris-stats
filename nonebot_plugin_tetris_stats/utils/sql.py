from sqlite3 import connect, Connection
import os

from nonebot import get_driver
from nonebot.log import logger


_DB_FILE = 'data/nonebot_plugin_tetris_stats/data.db'
_DB: Connection | None = None

driver = get_driver()


@driver.on_startup
async def _():
    '''初始化数据库'''
    await init_db()


@driver.on_shutdown
async def _():
    if isinstance(_DB, Connection):
        await _DB.close()


async def init_db() -> Connection:
    '''初始化数据库'''
    if not os.path.exists(os.path.dirname(_DB_FILE)):
        if os.path.exists('data/nonebot-plugin-tetris-stats'):  # 重命名旧的数据库路径
            os.rename('data/nonebot-plugin-tetris-stats',
                      os.path.dirname(_DB_FILE))
        else:
            os.makedirs(os.path.dirname(_DB_FILE))
    global _DB
    _DB = connect(_DB_FILE)
    cursor = _DB.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS IOBIND
                    (QQ INTEGER NOT NULL,
                    USER TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS TOPBIND
                    (QQ INTEGER NOT NULL,
                    USER TEXT NOT NULL)''')
    _DB.commit()
    logger.info('数据库初始化完成')
    return _DB


async def get_db() -> Connection:
    '''获取数据库对象'''
    return _DB or await init_db()


async def query_bind_info(qq_number: str | int, game_type: str) -> str | None:
    '''查询绑定信息'''
    db = await get_db()
    cursor = db.cursor()
    cursor.execute(f'SELECT USER FROM {game_type}BIND WHERE QQ = {qq_number}')
    user = cursor.fetchone()
    db.commit()
    if user is None:
        return None
    return user[0]


async def write_bind_info(qq_number: str | int, user: str, game_type: str) -> str:
    '''写入绑定信息'''
    bind_info = await query_bind_info(qq_number, game_type)
    db = await get_db()
    cursor = db.cursor()
    if bind_info is not None:
        cursor.execute(
            f'UPDATE {game_type}BIND SET USER = ? WHERE QQ = ?', (user, qq_number))
        message = '更新成功'
    elif bind_info is None:
        cursor.execute(
            f'INSERT INTO {game_type}BIND (QQ, USER) VALUES (?, ?)', (qq_number, user))
        message = '绑定成功'
    db.commit()
    return message
