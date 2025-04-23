from playwright.async_api import BrowserContext, TimeoutError, ViewportSize  # noqa: A004

from ..config.config import config
from .browser import BrowserManager
from .retry import retry
from .time_it import time_it


async def context_factory() -> BrowserContext:
    return await (await BrowserManager.get_browser()).new_context(device_scale_factor=config.tetris.screenshot_quality)


@retry(exception_type=TimeoutError, reply='截图失败, 重试中')
@time_it
async def screenshot(url: str) -> bytes:
    context = await BrowserManager.get_context('screenshot', factory=context_factory)
    async with await context.new_page() as page:
        await page.goto(url)
        await page.wait_for_selector('#content')
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
        return await page.locator('id=content').screenshot(animations='disabled', timeout=5000, type='png')
