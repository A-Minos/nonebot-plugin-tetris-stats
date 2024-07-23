from asyncio.subprocess import PIPE, Process, create_subprocess_exec
from enum import Enum, auto
from pathlib import Path
from shutil import rmtree
from typing import NamedTuple

from nonebot import get_driver
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import Alconna, Args, Option, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_localstore import get_data_dir  # type: ignore[import-untyped]

driver = get_driver()

templates_dir = get_data_dir('nonebot_plugin_tetris_stats') / 'templates'

alc = on_alconna(Alconna('更新模板', Option('--revision', Args['revision', str], alias={'-R'})), permission=SUPERUSER)

logger.level('GIT', no=10, color='<blue>')


class Status(Enum):
    OK = auto()
    NOT_EXIST = auto()
    NOT_INITIALIZATION = auto()


class Output(NamedTuple):
    stdout: list[str]
    stderr: list[str]


async def parse_log(proc: Process) -> Output:
    stdout, stderr = await proc.communicate()
    for i in (out := stdout.decode().splitlines()):
        logger.log('GIT', f'stdout: {i}')
    # stderr 可能是 None
    for i in (err := (stderr or b'').decode().splitlines()):
        logger.log('GIT', f'stderr: {i}')
    return Output(out, err)


async def check_git() -> None:
    try:
        await parse_log(await create_subprocess_exec('git', '--version', stdout=PIPE))
    except FileNotFoundError as e:
        msg = '未找到 git, 请确保 git 已安装并在环境变量中\n安装步骤请参阅: https://git-scm.com/book/zh/v2/%E8%B5%B7%E6%AD%A5-%E5%AE%89%E8%A3%85-Git'
        raise RuntimeError(msg) from e


async def check_repo(repo_path: Path) -> Status:
    if not repo_path.exists():
        return Status.NOT_EXIST
    proc = await create_subprocess_exec(
        'git', 'rev-parse', '--is-inside-work-tree', stdout=PIPE, stderr=PIPE, cwd=repo_path
    )
    await parse_log(proc)
    if proc.returncode != 0:
        return Status.NOT_INITIALIZATION
    return Status.OK


async def clone_repo(repo_url: str, repo_path: Path, branch: str | None = None, depth: int | None = 1) -> bool:
    args: list[str | Path] = ['git', 'clone', repo_url, repo_path]
    if branch is not None:
        args.extend(['-b', branch])
    if depth is not None:
        args.append(f'--depth={depth}')
    proc = await create_subprocess_exec(*args, stdout=PIPE, stderr=PIPE)
    await parse_log(proc)
    return proc.returncode == 0


async def checkout(revision: str, repo_path: Path) -> bool:
    proc = await create_subprocess_exec('git', 'checkout', revision, stdout=PIPE, stderr=PIPE, cwd=repo_path)
    await parse_log(proc)
    return proc.returncode == 0


async def init_templates() -> None:
    await check_git()
    status = await check_repo(templates_dir)
    if status == Status.OK:
        return
    if status == Status.NOT_EXIST:
        logger.info('模板仓库不存在, 正在尝试初始化...')
    if status == Status.NOT_INITIALIZATION:
        logger.warning('模板仓库状态异常, 尝试重新初始化')
        rmtree(templates_dir)
    if not await clone_repo(
        repo_url='https://github.com/A-Minos/tetris-stats-templates', repo_path=templates_dir, branch='gh-pages'
    ):
        msg = '模板仓库初始化失败'
        raise RuntimeError(msg)
    logger.success('模板仓库初始化成功')


async def update_templates(repo_path: Path) -> bool:
    logger.info('开始更新模板仓库...')
    logger.info('拉取最新提交')
    proc = await create_subprocess_exec('git', 'fetch', '--all', '--tags', stdout=PIPE, stderr=PIPE, cwd=repo_path)
    await parse_log(proc)
    if proc.returncode != 0:
        logger.error('拉取最新提交失败')
        return False
    logger.success('拉取最新提交成功')
    return True


async def check_commit_hash(commit_hash: str, repo_path: Path, branch: str | None = None) -> bool:
    output = await parse_log(
        proc := await create_subprocess_exec(
            'git', 'branch', '--contains', commit_hash, stdout=PIPE, stderr=PIPE, cwd=repo_path
        )
    )
    return (
        proc.returncode == 0
        and len(output.stdout) > 0
        and (branch is None or branch in output.stdout[0] or 'HEAD detached at' in output.stdout[0])
    )


async def handle_tag(tag: str) -> str | None:
    tags = (
        await parse_log(await create_subprocess_exec('git', 'tag', stdout=PIPE, stderr=PIPE, cwd=templates_dir))
    ).stdout
    if tag not in tags:
        logger.debug(f'{tag} 不为 tag')
        return None
    logger.info(f'{tag} 为 tag, 正在尝试 checkout 到 tag 对应的 gh-pages commit')
    tag_commit_hash = (
        (
            await parse_log(
                await create_subprocess_exec(
                    'git', 'show-ref', '--tags', tag, stdout=PIPE, stderr=PIPE, cwd=templates_dir
                )
            )
        )
        .stdout[0]
        .split(maxsplit=1)[0]
    )
    logger.success(f'tag 的 commit 为 {tag_commit_hash}')
    commit_hash = (
        await parse_log(
            await create_subprocess_exec(
                'git',
                'log',
                'gh-pages',
                '--grep',
                f'deploy: {tag_commit_hash}',
                '--pretty=format:%H',
                stdout=PIPE,
                stderr=PIPE,
                cwd=templates_dir,
            )
        )
    ).stdout[0]
    logger.info(f'找到疑似的 gh-pages commit {commit_hash}')
    if await check_commit_hash(commit_hash, templates_dir, branch='gh-pages'):
        logger.success('验证成功')
        return commit_hash
    logger.error('验证失败')
    return None


@alc.handle()
async def _(revision: str):
    if not await update_templates(templates_dir):
        msg = '模板仓库更新失败'
        logger.error(msg)
        await UniMessage(msg).finish()
    commit_hash = await handle_tag(revision)
    if commit_hash is not None:
        if await checkout(commit_hash, templates_dir):
            msg = f'模板成功 checkout 到 {commit_hash}'
            logger.success(msg)
            await alc.finish(msg)
        else:
            logger.error('checkout 失败')
            await alc.finish('checkout 失败')


@driver.on_startup
async def _():
    await init_templates()
