from nonebot import get_plugin_config
from playwright.async_api import TimeoutError, ViewportSize

from ..config.config import Config
from .browser import BrowserManager
from .retry import retry

config = get_plugin_config(Config)


@retry(exception_type=TimeoutError, reply='截图失败, 重试中')
async def screenshot(url: str) -> bytes:
    browser = await BrowserManager.get_browser()
    async with (
        await browser.new_page(device_scale_factor=config.tetris_screenshot_quality) as page,
    ):
        await page.goto(url)
        await page.wait_for_load_state('networkidle')
        size: ViewportSize = await page.evaluate("""
            () => {
                const element = document.querySelector('#content');
                return {
                    width: element.offsetWidth,
                    height: element.offsetHeight,
                };
            };
        """)
        await page.set_viewport_size(size)
        return await page.locator('id=content').screenshot(timeout=5000, type='png')
