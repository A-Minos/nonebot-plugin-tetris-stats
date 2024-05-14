import sys
from os import environ
from platform import system
from re import sub

from nonebot import get_driver
from nonebot.log import logger
from playwright.__main__ import main
from playwright.async_api import Browser, async_playwright

driver = get_driver()

global_config = driver.config


@driver.on_startup
async def _():
    await BrowserManager.init_playwright()


@driver.on_shutdown
async def _():
    await BrowserManager.close_browser()


class BrowserManager:
    """浏览器管理类"""

    _browser: Browser | None = None

    @classmethod
    async def init_playwright(cls) -> None:
        if system() == 'Windows' and getattr(global_config, 'fastapi_reload', False):
            msg = '加载失败, Windows 必须设置 FASTAPI_RELOAD=false 才能正常运行 playwright'
            raise ImportError(msg)
        logger.info('开始 安装/更新 playwright 浏览器')
        environ['PLAYWRIGHT_DOWNLOAD_HOST'] = 'https://npmmirror.com/mirrors/playwright/'
        if cls._call_playwright(['', 'install', 'firefox']):
            logger.success('安装/更新 playwright 浏览器成功')
        else:
            logger.warning('playwright 浏览器 安装/更新 失败, 尝试使用原始仓库下载')
            del environ['PLAYWRIGHT_DOWNLOAD_HOST']
            if cls._call_playwright(['', 'install', 'firefox']):
                logger.success('安装/更新 playwright 浏览器成功')
            else:
                logger.error('安装/更新 playwright 浏览器失败')
        try:
            await cls._start_browser()
        except BaseException as e:  # 不知道会有什么异常, 交给用户解决
            msg = 'playwright 启动失败, 请尝试在命令行运行 playwright install-deps firefox, 如果仍然启动失败, 请参考上面的报错👆'
            raise ImportError(msg) from e
        else:
            logger.success('playwright 启动成功')

    @classmethod
    def _call_playwright(cls, argv: list[str]) -> bool:
        """等价于调用 playwright 的命令行程序"""
        argv_backup = sys.argv.copy()
        sys.argv[0] = sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
        sys.argv = argv
        try:
            main()
        except SystemExit as e:
            return e.code == 0
        except BaseException:  # noqa: BLE001
            return False
        finally:
            sys.argv = argv_backup
        return True

    @classmethod
    async def _start_browser(cls) -> Browser:
        """启动浏览器实例"""
        playwright = await async_playwright().start()
        cls._browser = await playwright.firefox.launch()
        return cls._browser

    @classmethod
    async def get_browser(cls) -> Browser:
        """获取浏览器实例"""
        return cls._browser or await cls._start_browser()

    @classmethod
    async def close_browser(cls) -> None:
        """关闭浏览器实例"""
        if isinstance(cls._browser, Browser):
            await cls._browser.close()
