from nonebot.log import logger

import sqlite3
import os

_DB_FILE = 'data/nonebot-plugin-tetris-stats/data.db'

# 初始化数据库
async def initDB():
    if not os.path.exists(os.path.dirname(_DB_FILE)):
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

# 查询绑定信息
async def queryBindInfo(QQNumber: int, gameType: str) -> dict:
    db = sqlite3.connect(_DB_FILE)
    cursor = db.cursor()
    cursor.execute(f'SELECT USER FROM {gameType}BIND WHERE QQ = {QQNumber}')
    user = cursor.fetchone()
    db.commit()
    db.close()
    if user is None:
        return {'Hit': False, 'User': None}
    else:
        return {'Hit': True, 'User': user[0]}

# 写入绑定信息
async def writeBindInfo(QQNumber: int, user: str, gameType: str) -> str:
    info = await queryBindInfo(QQNumber, gameType)
    db = sqlite3.connect(_DB_FILE)
    cursor = db.cursor()
    if info['Hit'] is True:
        cursor.execute(
            f'UPDATE {gameType}BIND SET USER = ? WHERE QQ = ?', (user, QQNumber))
        message = '更新成功'
    elif info['Hit'] is False:
        cursor.execute(
            f'INSERT INTO {gameType}BIND (QQ, USER) VALUES (?, ?)', (QQNumber, user))
        message = '绑定成功'
    db.commit()
    db.close()
    return message
