from nonebot import get_driver

from .Utils.SQL import initDB

from . import GameDataProcessor


driver = get_driver()


@driver.on_startup
async def startUP():
    await initDB()
