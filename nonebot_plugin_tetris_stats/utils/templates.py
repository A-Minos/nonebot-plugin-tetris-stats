from hashlib import sha256
from http import HTTPStatus
from pathlib import Path
from shutil import rmtree
from time import time_ns
from zipfile import ZipFile

from aiofiles import open as aopen
from httpx import AsyncClient
from nonebot import get_driver
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import Alconna, Args, Option, on_alconna
from rich.progress import Progress

from ..config.config import CACHE_PATH, DATA_PATH, config

driver = get_driver()

TEMPLATES_DIR = DATA_PATH / 'templates'

alc = on_alconna(Alconna('更新模板', Option('--revision', Args['revision', str], alias={'-R'})), permission=SUPERUSER)


async def download_templates(tag: str) -> Path:
    logger.info(f'开始下载模板 {tag}')
    async with AsyncClient(proxy=config.tetris.proxy.github or config.tetris.proxy.main) as client:
        if tag == 'latest':
            logger.info('目标为 latest, 正在获取最新版本号')
            tag = (
                (
                    await client.get(
                        'https://github.com/A-Minos/tetris-stats-templates-new/releases/latest', follow_redirects=True
                    )
                )
                .url.path.strip('/')
                .rsplit('/', 1)[-1]
            )
            logger.success(f'获取到的最新版本号: {tag}')
        path = CACHE_PATH / f'dist_{time_ns()}.zip'
        with Progress() as progress:
            task_id = progress.add_task('[red]Downloading...', total=None)
            async with (
                client.stream(
                    'GET',
                    f'https://github.com/A-Minos/tetris-stats-templates-new/releases/download/{tag}/dist.zip',
                    follow_redirects=True,
                ) as response,
                aopen(path, 'wb') as file,
            ):
                response.raise_for_status()
                progress.update(task_id, total=int(response.headers.get('content-length', 0)) or None)
                async for chunk in response.aiter_bytes():
                    await file.write(chunk)
                    progress.update(task_id, advance=len(chunk))
        logger.success('模板下载完成')
        return path


def unzip_templates(zip_path: Path) -> Path:
    logger.info('开始解压模板')
    temp_path = TEMPLATES_DIR.parent / f'temp_{time_ns()}'
    with ZipFile(zip_path) as zip_file:
        zip_file.extractall(temp_path)
    zip_path.unlink()
    logger.success('模板解压完成')
    return temp_path


async def check_hash(hash_file_path: Path) -> bool:
    logger.info('开始校验模板哈希值')
    for i in hash_file_path.read_text().splitlines():
        file_sha256, file_relative_path = i.split(maxsplit=1)
        file_path = hash_file_path.parent / file_relative_path
        hasher = sha256()
        if not file_path.is_file():
            logger.error(f'{file_path.name} 不存在或不是文件')
            return False
        async with aopen(file_path, 'rb') as file:
            while True:
                chunk = await file.read(65535)
                if not chunk:
                    break
                hasher.update(chunk)
        if hasher.hexdigest() != file_sha256:
            logger.error(f'{file_path.name} hash 不匹配')
            return False
        logger.debug(f'{file_path.name} hash 匹配成功')
    logger.success('模板哈希值校验成功')
    return True


async def init_templates(tag: str) -> bool:
    logger.info(f'开始初始化模板 {tag}')
    temp_path = unzip_templates(await download_templates(tag))
    if not await check_hash(temp_path / 'hash.sha256'):
        rmtree(temp_path)
        return False
    if TEMPLATES_DIR.exists():
        logger.info('清除旧模板文件')
        rmtree(TEMPLATES_DIR)
    temp_path.rename(TEMPLATES_DIR)
    logger.info('模板初始化完成')
    return True


async def check_tag(tag: str) -> bool:
    async with AsyncClient(proxy=config.tetris.proxy.github or config.tetris.proxy.main) as client:
        return (
            await client.get(f'https://github.com/A-Minos/tetris-stats-templates-new/releases/tag/{tag}')
        ).status_code != HTTPStatus.NOT_FOUND


@driver.on_startup
async def _():
    if (path := (TEMPLATES_DIR / 'hash.sha256')).is_file() and await check_hash(path):
        logger.success('模板验证成功')
        return
    if not await init_templates('latest'):
        msg = '模板初始化失败'
        raise RuntimeError(msg)


@alc.handle()
async def _(revision: str | None = None):
    if revision is not None and not await check_tag(revision):
        await alc.finish(f'{revision} 不是模板仓库中的有效标签')
    logger.info('开始更新模板')
    if await init_templates(revision or 'latest'):
        await alc.finish('更新模板成功')
    await alc.finish('更新模板失败')
