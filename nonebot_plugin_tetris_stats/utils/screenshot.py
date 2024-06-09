from playwright.async_api import TimeoutError

from .browser import BrowserManager
from .retry import retry


@retry(exception_type=TimeoutError, reply='截图失败, 重试中')
async def screenshot(url: str) -> bytes:
    browser = await BrowserManager.get_browser()
    async with (
        await browser.new_page(viewport={'width': 3000, 'height': 3000}) as page,
    ):
        await page.goto(url)
        await page.wait_for_load_state('networkidle')
        return await page.locator('id=content').screenshot(timeout=5000, type='png')
