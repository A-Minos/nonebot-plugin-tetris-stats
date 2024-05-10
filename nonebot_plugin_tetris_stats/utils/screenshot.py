from .browser import BrowserManager


async def screenshot(url: str) -> bytes:
    browser = await BrowserManager.get_browser()
    async with (
        await browser.new_page(no_viewport=True, viewport={'width': 0, 'height': 0}) as page,
    ):
        await page.goto(url)
        await page.wait_for_load_state('networkidle')
        return await page.screenshot(full_page=True, type='png')
