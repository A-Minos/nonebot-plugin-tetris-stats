from playwright.async_api import TimeoutError, ViewportSize

from ..config.config import config
from .browser import BrowserManager
from .retry import retry
from .time_it import time_it


@retry(exception_type=TimeoutError, reply='截图失败, 重试中')
@time_it
async def screenshot(url: str) -> bytes:
    browser = await BrowserManager.get_browser()
    async with (
        await browser.new_page(device_scale_factor=config.tetris.screenshot_quality) as page,
    ):
        await page.goto(url)
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
        await page.wait_for_load_state('networkidle')
        return await page.locator('id=content').screenshot(animations='disabled', timeout=5000, type='png')
