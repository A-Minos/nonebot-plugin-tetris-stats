from asyncio import Condition
from contextlib import suppress

from playwright.async_api import BrowserContext, Page, TimeoutError  # noqa: A004

from ..config.config import config
from ..i18n import Lang
from .browser import BrowserManager
from .retry import retry
from .time_it import time_it


class PagePool:
    """固定的渲染页池: 容量按已创建的页面数算, 每个页面同时只渲染一张图

    每次 new_page 都要重开一个内容进程, Firefox 上约 0.7s, 复用页面能把渲染降到 0.3s 左右
    """

    def __init__(self, size: int) -> None:
        self._size = size
        self._pages: list[Page] = []
        self._idle: list[Page] = []
        self._condition = Condition()

    async def acquire(self, context: BrowserContext) -> Page:
        async with self._condition:
            while True:
                while self._idle:
                    page = self._idle.pop()
                    if page.is_closed():
                        self._pages.remove(page)
                        continue
                    return page
                if len(self._pages) < self._size:
                    page = await context.new_page()
                    self._pages.append(page)
                    return page
                await self._condition.wait()

    async def release(self, page: Page) -> None:
        async with self._condition:
            if page.is_closed():
                if page in self._pages:
                    self._pages.remove(page)
            else:
                self._idle.append(page)
            self._condition.notify_all()

    async def discard(self, page: Page) -> None:
        with suppress(Exception):
            await page.close()
        await self.release(page)


pool = PagePool(config.tetris.screenshot_pool_size)


async def context_factory() -> BrowserContext:
    return await (await BrowserManager.get_browser()).new_context(device_scale_factor=config.tetris.screenshot_quality)


@retry(exception_type=TimeoutError, reply=Lang.retry.screenshot)
@time_it
async def screenshot(url: str) -> bytes:
    context = await BrowserManager.get_context('screenshot', factory=context_factory)
    page = await pool.acquire(context)
    try:
        # 从默认视口开始, 和新建 page 时的初始状态一致
        await page.set_viewport_size({'width': 1280, 'height': 720})
        await page.goto(url)
        await page.wait_for_selector('#content')
        # 字体和图片没就绪时字形和度量都不是最终状态
        for expression in (
            "document.fonts.status === 'loaded'",
            '() => [...document.images].every((image) => image.complete)',
        ):
            with suppress(TimeoutError):
                await page.wait_for_function(expression, timeout=3000)
        await page.set_viewport_size(
            await page.evaluate(
                """
                () => {
                    const element = document.querySelector('#content');
                    return {width: element.offsetWidth, height: element.offsetHeight};
                }
                """
            )
        )
        # 改视口会重新布局, 等两帧绘制落地再截; 用带超时的 wait_for_function, evaluate 没有超时
        with suppress(TimeoutError):
            await page.wait_for_function(
                '() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))',
                timeout=3000,
            )
        image = await page.locator('id=content').screenshot(animations='disabled', timeout=5000, type='png')
    except BaseException:
        await pool.discard(page)
        raise
    await pool.release(page)
    return image
