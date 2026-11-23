from typing import Annotated, TypeAlias

from arclet.alconna import Arg
from nonebot.params import Depends
from nonebot_plugin_alconna import Args, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ...db import trigger
from ...i18n import Lang
from ...utils.exception import MessageFormatError, NeedCatchError
from . import alc, assign, command, get_player
from .api import Player
from .constant import GAME_TYPE
from .models import TETRIOPlayerAlias


async def resolve_player(who: str) -> Player:
    uid = None
    if not who.startswith('~'):
        async with get_session() as session:
            entry = await session.get(TETRIOPlayerAlias, who)
        if entry is not None:
            uid = entry.uid
    try:
        return get_player(uid or who.removeprefix('~'))
    except MessageFormatError as error:
        await UniMessage(error.render()).finish()


PlayerDep: TypeAlias = Annotated[Player, Depends(resolve_player)]


command.add(
    Subcommand(
        'alias',
        Subcommand(
            'add',
            Args(Arg('alias', str), Arg('account', get_player)),
            help_text=Lang.command.tetrio.alias.add.description.cast(),
        ),
        Subcommand('remove', Args(Arg('alias', str)), help_text=Lang.command.tetrio.alias.remove.description.cast()),
        Subcommand('list', Args(Arg('who', str)), help_text=Lang.command.tetrio.alias.list.description.cast()),
        help_text=Lang.command.tetrio.alias.description.cast(),
    ),
)

alc.shortcut(
    r'(?i:io)\s*(?i:alias)',
    command='tstats TETR.IO alias',
    humanized=Lang.command.tetrio.alias.shortcut.cast(),
)


@assign('TETRIO.alias.add', default_available=False)
async def _(alias: str, account: Player, event_session: Uninfo):
    if '~' in alias:
        raise NeedCatchError(Lang.alias.reserved_character)
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='alias',
        command_args=['add'],
    ):
        uid = (await account.user).ID
        async with get_session() as session:
            session.add(TETRIOPlayerAlias(alias=alias, uid=uid))
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                selected = await session.get(TETRIOPlayerAlias, alias)
                if selected is None:
                    raise
                if selected.uid != uid:
                    raise NeedCatchError(Lang.alias.conflict, alias=alias) from error
        await UniMessage(Lang.alias.saved(alias=alias)).finish()


@assign('TETRIO.alias.remove', default_available=False)
async def _(alias: str, event_session: Uninfo):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='alias',
        command_args=['remove'],
    ):
        async with get_session() as session:
            entry = await session.get(TETRIOPlayerAlias, alias)
            if entry is None:
                raise NeedCatchError(Lang.alias.not_found, alias=alias)
            await session.delete(entry)
            await session.commit()
        await UniMessage(Lang.alias.removed(alias=alias)).finish()


@assign('TETRIO.alias.list', default_available=False)
async def _(player: PlayerDep, event_session: Uninfo):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='alias',
        command_args=['list'],
    ):
        uid = player.user_id or (await player.user).ID
        async with get_session() as session:
            aliases = (await session.scalars(select(TETRIOPlayerAlias.alias).where(TETRIOPlayerAlias.uid == uid))).all()
        await UniMessage('\n'.join(aliases) if aliases else Lang.alias.empty()).finish()
