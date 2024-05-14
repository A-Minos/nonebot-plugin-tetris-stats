from asyncio.subprocess import PIPE, create_subprocess_exec
from shutil import rmtree

from nonebot import get_driver
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import on_alconna
from nonebot_plugin_localstore import get_data_dir  # type: ignore[import-untyped]

driver = get_driver()

templates_dir = get_data_dir('nonebot_plugin_tetris_stats') / 'templates'

alc = on_alconna('更新模板', permission=SUPERUSER)


@driver.on_startup
async def init_templates() -> None:
    try:
        await create_subprocess_exec('git', '--version', stdout=PIPE)
    except FileNotFoundError as e:
        msg = '未找到 git, 请确保 git 已安装并在环境变量中\n安装步骤请参阅: https://git-scm.com/book/zh/v2/%E8%B5%B7%E6%AD%A5-%E5%AE%89%E8%A3%85-Git'
        raise RuntimeError(msg) from e
    if not templates_dir.exists():
        logger.info('模板仓库不存在, 正在尝试初始化...')
        proc = await create_subprocess_exec(
            'git',
            'clone',
            '-b',
            'gh-pages',
            'https://github.com/A-Minos/tetris-stats-templates',
            templates_dir,
            '--depth=1',
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            for i in stderr.decode().splitlines():
                logger.error(i)
            msg = '初始化模板仓库失败'
            raise RuntimeError(msg)
        logger.success('模板仓库初始化成功')
        return
    proc = await create_subprocess_exec(
        'git', 'rev-parse', '--is-inside-work-tree', stdout=PIPE, stderr=PIPE, cwd=templates_dir
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        for i in stderr.decode().splitlines():
            logger.error(i)
        logger.warning('模板仓库状态异常, 尝试重新初始化')
        rmtree(templates_dir)
        await init_templates()
        return
    logger.info('正在更新模板仓库...')
    proc = await create_subprocess_exec('git', 'pull', stdout=PIPE, stderr=PIPE, cwd=templates_dir)
    stdout, stderr = await proc.communicate()
    logger.info(stdout.decode().strip())
    if proc.returncode != 0:
        for i in stderr.decode().splitlines():
            logger.error(i)
        msg = '更新模板仓库失败'
        raise RuntimeError(msg)
    logger.success('模板仓库更新成功')


@alc.handle()
async def _():
    await init_templates()
    await alc.finish('模板仓库更新成功')
