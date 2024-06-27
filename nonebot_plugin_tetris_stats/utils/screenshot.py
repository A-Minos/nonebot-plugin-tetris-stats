from nonebot import get_plugin_config
from playwright.async_api import TimeoutError

from ..config.config import Config
from .browser import BrowserManager
from .retry import retry

config = get_plugin_config(Config)


@retry(exception_type=TimeoutError, reply='截图失败, 重试中')
async def screenshot(url: str) -> bytes:
    browser = await BrowserManager.get_browser()
    async with (
        await browser.new_page(
            viewport={'width': 3000, 'height': 3000}, device_scale_factor=config.tetris_screenshot_quality
        ) as page,
    ):
        await page.goto(url)
        await page.wait_for_load_state('networkidle')
        return await page.locator('id=content').screenshot(timeout=5000, type='png')
