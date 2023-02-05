import sys
from os import environ
from platform import system

from nonebot import get_driver
from nonebot.log import logger
from playwright.__main__ import main
from playwright.async_api import async_playwright

driver = get_driver()

global_config = driver.config


@driver.on_startup
async def _():
    await BrowserManager._init_playwright()


class BrowserManager:
    @classmethod
    async def _init_playwright(cls):
        if system() == 'Windows' and getattr(global_config, 'fastapi_reload', False):
            raise ImportError(
                '加载失败, Windows 必须设置 FASTAPI_RELOAD=false 才能正常运行 playwright'
            )
        logger.info('开始 安装/更新 playwright 浏览器')
        environ[
            'PLAYWRIGHT_DOWNLOAD_HOST'
        ] = 'https://npmmirror.com/mirrors/playwright/'
        if await cls._handle_error(
            await cls.call_playwright(['', 'install', 'firefox'])
        ):
            logger.success('安装/更新 playwright 浏览器成功')
        else:
            logger.warning('playwright 浏览器 安装/更新 失败, 尝试使用原始仓库下载')
            del environ['PLAYWRIGHT_DOWNLOAD_HOST']
            if await cls._handle_error(
                await cls.call_playwright(['', 'install', 'firefox'])
            ):
                logger.success('安装/更新 playwright 浏览器成功')
            else:
                logger.error('安装/更新 playwright 浏览器失败')
        try:
            async with async_playwright() as playwright:
                await playwright.firefox.launch()
        except Exception as e:
            raise ImportError(
                'playwright 启动失败, 请尝试在命令行运行 playwright install-deps firefox, 如果仍然启动失败, 请参考上面的报错👆'
            ) from e
        else:
            logger.success('playwright 启动成功')

    @classmethod
    async def call_playwright(cls, argv: list[str]) -> BaseException:
        """等价于调用 playwright 的命令行程序"""
        argv_backup = sys.argv.copy()
        from re import sub

        sys.argv[0] = sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
        sys.argv = argv
        try:
            main()
        except BaseException as e:
            return e
        finally:
            sys.argv = argv_backup
        return SystemExit(0)

    @classmethod
    async def _handle_error(cls, error: BaseException) -> bool:
        if isinstance(error, SystemExit) and error.code == 0:
            return True
        return False
