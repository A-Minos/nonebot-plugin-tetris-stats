from collections.abc import Collection, Iterator
from hashlib import md5
from typing import get_args

from arclet.alconna import Arg, MultiVar
from nonebot_plugin_alconna import Args, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from pydantic import BaseModel
from sqlalchemy import delete, select
from tarina.lang.model import LangItem

from ...i18n import Lang
from ...utils.render import pre_render
from ...utils.render.schemas.base import Avatar, Base, TETRIOPlayer
from . import alc, assign, command, get_player
from .api import Player
from .models import TETRIODisplayMask
from .typedefs import DisplayField

DISPLAY_FIELDS: tuple[DisplayField, ...] = get_args(DisplayField)
FIELD_LABELS: dict[DisplayField, LangItem] = {
    'name': Lang.mask.fields.name,
    'avatar': Lang.mask.fields.avatar,
    'banner': Lang.mask.fields.banner,
    'bio': Lang.mask.fields.bio,
    'country': Lang.mask.fields.country,
}

command.add(
    Subcommand(
        'mask',
        Subcommand(
            'add',
            Args(
                Arg('account', get_player, notice=Lang.command.tetrio.mask.add.args.account.notice.cast()),
                Arg('fields', MultiVar(str, '*'), notice=Lang.command.tetrio.mask.add.args.fields.notice.cast()),
            ),
            help_text=Lang.command.tetrio.mask.add.description.cast(),
        ),
        Subcommand(
            'remove',
            Args(
                Arg('account', get_player, notice=Lang.command.tetrio.mask.remove.args.account.notice.cast()),
                Arg('fields', MultiVar(str, '*'), notice=Lang.command.tetrio.mask.remove.args.fields.notice.cast()),
            ),
            help_text=Lang.command.tetrio.mask.remove.description.cast(),
        ),
        Subcommand('list', help_text=Lang.command.tetrio.mask.list.description.cast()),
        help_text=Lang.command.tetrio.mask.description.cast(),
    )
)

alc.shortcut(
    '(?i:io)屏蔽列表',
    command='tstats TETR.IO mask list',
    fuzzy=False,
    humanized=Lang.command.tetrio.mask.list.shortcut.cast(),
)
alc.shortcut(
    '(?i:io)屏蔽(?!列表)', command='tstats TETR.IO mask add', humanized=Lang.command.tetrio.mask.add.shortcut.cast()
)
alc.shortcut(
    '(?i:io)解屏蔽', command='tstats TETR.IO mask remove', humanized=Lang.command.tetrio.mask.remove.shortcut.cast()
)


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
    return ', '.join(FIELD_LABELS[field]() for field in DISPLAY_FIELDS if field in fields) or Lang.mask.none()


async def parse_fields(texts: tuple[str, ...]) -> frozenset[DisplayField]:
    """英文字段名始终可用, 另外接受当前语言的字段名"""
    lookup: dict[str, DisplayField] = {key: field for field in DISPLAY_FIELDS for key in (field, FIELD_LABELS[field]())}
    if unknown := [text for text in texts if text not in lookup]:
        await UniMessage(
            Lang.mask.invalid_field(
                fields=', '.join(unknown),
                available=', '.join(f'{field} ({FIELD_LABELS[field]()})' for field in DISPLAY_FIELDS),
            )
        ).finish()
    return frozenset(lookup[text] for text in texts) or frozenset(DISPLAY_FIELDS)


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
