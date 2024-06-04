from playwright.async_api import TimeoutError

from .browser import BrowserManager
from .retry import retry


@retry(exception_type=TimeoutError, reply='截图失败, 重试中')
async def screenshot(url: str) -> bytes:
    browser = await BrowserManager.get_browser()
    async with (
        await browser.new_page(no_viewport=True, viewport={'width': 0, 'height': 0}) as page,
    ):
        await page.goto(url)
        await page.wait_for_load_state('networkidle', timeout=5000)
        return await page.screenshot(timeout=5000, full_page=True, type='png')
