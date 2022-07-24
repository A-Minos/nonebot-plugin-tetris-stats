from nonebot.log import logger

import sqlite3
import os

_DB_FILE = 'data/nonebot_plugin_tetris_stats/data.db'


async def initDB():
    # 初始化数据库
    if not os.path.exists(os.path.dirname(_DB_FILE)):
        if os.path.exists('data/nonebot-plugin-tetris-stats'):  # 重命名旧的数据库路径
            os.rename('data/nonebot-plugin-tetris-stats',
                      os.path.dirname(_DB_FILE))
        else:
            os.makedirs(os.path.dirname(_DB_FILE))
    db = sqlite3.connect(_DB_FILE)
    cursor = db.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS IOBIND
                    (QQ INTEGER NOT NULL,
                    USER TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS TOPBIND
                    (QQ INTEGER NOT NULL,
                    USER TEXT NOT NULL)''')
    db.commit()
    db.close()
    logger.info('数据库初始化完成')


async def queryBindInfo(QQNumber: str | int, gameType: str) -> str | None:
    # 查询绑定信息
    db = sqlite3.connect(_DB_FILE)
    cursor = db.cursor()
    cursor.execute(f'SELECT USER FROM {gameType}BIND WHERE QQ = {QQNumber}')
    user = cursor.fetchone()
    db.commit()
    db.close()
    if user is None:
        return None
    else:
        return user[0]


async def writeBindInfo(QQNumber: str | int, user: str, gameType: str) -> str:
    # 写入绑定信息
    bindInfo = await queryBindInfo(QQNumber, gameType)
    db = sqlite3.connect(_DB_FILE)
    cursor = db.cursor()
    if bindInfo is not None:
        cursor.execute(
            f'UPDATE {gameType}BIND SET USER = ? WHERE QQ = ?', (user, QQNumber))
        message = '更新成功'
    elif bindInfo is None:
        cursor.execute(
            f'INSERT INTO {gameType}BIND (QQ, USER) VALUES (?, ?)', (QQNumber, user))
        message = '绑定成功'
    db.commit()
    db.close()
    return message
