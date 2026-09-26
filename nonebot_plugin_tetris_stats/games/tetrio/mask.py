from collections.abc import Collection, Iterator
from hashlib import md5
from typing import get_args

from arclet.alconna import Arg, MultiVar
from nonebot_plugin_alconna import Args, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from pydantic import BaseModel
from sqlalchemy import delete, select

from ...i18n import Lang
from ...utils.render import pre_render
from ...utils.render.schemas.base import Avatar, Base, TETRIOPlayer
from . import alc, assign, command, get_player
from .api import Player
from .models import TETRIODisplayMask
from .typedefs import DisplayField

DISPLAY_FIELDS: tuple[DisplayField, ...] = get_args(DisplayField)
FIELD_ALIASES: dict[str, DisplayField] = {
    **{field: field for field in DISPLAY_FIELDS},
    '名字': 'name',
    '昵称': 'name',
    '头像': 'avatar',
    '横幅': 'banner',
    '简介': 'bio',
    '国旗': 'country',
    '国家': 'country',
}

command.add(
    Subcommand(
        'mask',
        Subcommand(
            'add',
            Args(
                Arg('account', get_player, notice='TETR.IO 用户名 / ID'),
                Arg('fields', MultiVar(str, '*'), notice='屏蔽字段, 默认全部'),
            ),
            help_text='屏蔽玩家的展示信息',
        ),
        Subcommand(
            'remove',
            Args(
                Arg('account', get_player, notice='TETR.IO 用户名 / ID'),
                Arg('fields', MultiVar(str, '*'), notice='解除字段, 默认全部'),
            ),
            help_text='解除玩家的展示信息屏蔽',
        ),
        Subcommand('list', help_text='列出被屏蔽的玩家'),
        help_text='管理 TETR.IO 玩家展示信息屏蔽',
    )
)

alc.shortcut('(?i:io)屏蔽列表', command='tstats TETR.IO mask list', fuzzy=False, humanized='io屏蔽列表')
alc.shortcut('(?i:io)屏蔽(?!列表)', command='tstats TETR.IO mask add', humanized='io屏蔽')
alc.shortcut('(?i:io)解屏蔽', command='tstats TETR.IO mask remove', humanized='io解屏蔽')


async def get_masks(uids: Collection[str] | None = None) -> dict[str, frozenset[DisplayField]]:
    """查询玩家的屏蔽字段, 不传 uids 时返回全部"""
    statement = select(TETRIODisplayMask)
    if uids is not None:
        if not uids:
            return {}
        statement = statement.where(TETRIODisplayMask.uid.in_(uids))
    masks: dict[str, set[DisplayField]] = {}
    async with get_session() as session:
        for row in await session.scalars(statement):
            masks.setdefault(row.uid, set()).add(row.field)
    return {uid: frozenset(fields) for uid, fields in masks.items()}


async def get_mask(uid: str) -> frozenset[DisplayField]:
    return (await get_masks([uid])).get(uid, frozenset())


def display_name(name: str, fields: Collection[DisplayField]) -> str:
    """给不经过渲染钩子的纯文本使用"""
    return Lang.mask.name() if 'name' in fields else name


def iter_players(obj: object) -> Iterator[TETRIOPlayer]:
    if isinstance(obj, TETRIOPlayer):
        yield obj
    if isinstance(obj, BaseModel):
        values: Collection[object] = vars(obj).values()
    elif isinstance(obj, list | tuple | set):
        values = obj
    elif isinstance(obj, dict):
        values = obj.values()
    else:
        return
    for value in values:
        yield from iter_players(value)


def apply_mask(player: TETRIOPlayer, fields: Collection[DisplayField]) -> None:
    replacements: dict[DisplayField, object] = {
        'name': Lang.mask.name(),
        'avatar': Avatar(type='identicon', hash=md5(player.id.encode()).hexdigest()),  # noqa: S324
        'banner': None,
        'bio': None,
        'country': None,
    }
    present = vars(player)
    for field in fields:
        if field in present:
            setattr(player, field, replacements[field])


@pre_render
async def _(data: Base) -> None:
    players = list(iter_players(data))
    masks = await get_masks({player.id for player in players})
    for player in players:
        if player.id in masks:
            apply_mask(player, masks[player.id])


def format_fields(fields: Collection[DisplayField]) -> str:
    return ', '.join(field for field in DISPLAY_FIELDS if field in fields) or Lang.mask.none()


async def parse_fields(fields: tuple[str, ...]) -> frozenset[DisplayField]:
    if unknown := [field for field in fields if field not in FIELD_ALIASES]:
        await UniMessage(Lang.mask.invalid_field(fields=', '.join(unknown))).finish()
    return frozenset(FIELD_ALIASES[field] for field in fields) or frozenset(DISPLAY_FIELDS)


@assign('TETRIO.mask.add', default_available=False)
async def _(account: Player, fields: tuple[str, ...]):
    selected = await parse_fields(fields)
    uid = account.user_id or (await account.user).ID
    async with get_session() as session:
        for field in selected:
            await session.merge(TETRIODisplayMask(uid=uid, field=field))
        await session.commit()
    await UniMessage(Lang.mask.updated(uid=uid, fields=format_fields(await get_mask(uid)))).finish()


@assign('TETRIO.mask.remove', default_available=False)
async def _(account: Player, fields: tuple[str, ...]):
    selected = await parse_fields(fields)
    uid = account.user_id or (await account.user).ID
    async with get_session() as session:
        await session.execute(
            delete(TETRIODisplayMask).where(TETRIODisplayMask.uid == uid, TETRIODisplayMask.field.in_(selected))
        )
        await session.commit()
    await UniMessage(Lang.mask.updated(uid=uid, fields=format_fields(await get_mask(uid)))).finish()


@assign('TETRIO.mask.list', default_available=False)
async def _():
    masks = await get_masks()
    await UniMessage(
        '\n'.join(f'{uid}: {format_fields(fields)}' for uid, fields in sorted(masks.items())) or Lang.mask.empty()
    ).finish()
