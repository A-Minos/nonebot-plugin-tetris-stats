from dataclasses import dataclass

from arclet.alconna import Arg
from nonebot_plugin_alconna import Args, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from ...i18n import Lang
from ...utils.exception import MessageFormatError, NeedCatchError
from . import alc, assign, command, get_player
from .api import Player
from .constant import USER_NAME
from .models import TETRIOPlayerAlias, TETRIOUserUniqueIdentifier
from .uid import ensure_uid_ids, player_insert


@dataclass(frozen=True)
class AliasRef:
    name: str


def normalize_alias(value: str) -> str:
    if not USER_NAME.fullmatch(value):
        raise MessageFormatError(Lang.alias.invalid)
    return value.lower()


def parse_query_target(value: str) -> Player | AliasRef:
    if value.startswith('~'):
        return AliasRef(normalize_alias(value[1:]))
    return get_player(value)


async def _find_alias_uid(alias: str) -> str | None:
    async with get_session() as session:
        return await session.scalar(
            select(TETRIOUserUniqueIdentifier.user_unique_identifier)
            .join(TETRIOPlayerAlias, TETRIOPlayerAlias.uid_id == TETRIOUserUniqueIdentifier.id)
            .where(TETRIOPlayerAlias.alias == alias)
        )


async def resolve_query_player(target: Player | AliasRef) -> Player:
    if isinstance(target, AliasRef):
        uid = await _find_alias_uid(target.name)
        if uid is None:
            raise NeedCatchError(Lang.alias.not_found, alias=target.name)
        return Player(user_id=uid, trust=True)

    if target.user_name is not None and (uid := await _find_alias_uid(target.user_name.lower())) is not None:
        return Player(user_id=uid, trust=True)
    return target


async def save_alias(alias: str, uid: str) -> bool:
    async with get_session() as session:
        uid_id = (await ensure_uid_ids(session, {uid}))[uid]
        await session.execute(
            player_insert(session, TETRIOPlayerAlias)
            .values(alias=alias, uid_id=uid_id)
            .on_conflict_do_nothing(index_elements=[TETRIOPlayerAlias.alias])
        )
        selected = await session.get(TETRIOPlayerAlias, alias)
        if selected is None or selected.uid_id != uid_id:
            await session.rollback()
            return False
        await session.commit()
        return True


command.add(
    Subcommand(
        'alias',
        Subcommand(
            'add',
            Args(Arg('alias', str), Arg('account', get_player)),
            help_text=Lang.command.tetrio.alias.add.description.cast(),
        ),
        Subcommand('remove', Args(Arg('alias', str)), help_text=Lang.command.tetrio.alias.remove.description.cast()),
        help_text=Lang.command.tetrio.alias.description.cast(),
    ),
)

alc.shortcut('(?i:ioalias)', command='tstats TETR.IO alias', humanized=Lang.command.tetrio.alias.shortcut.cast())


@assign('TETRIO.alias.add', default_available=False)
async def _(alias: str, account: Player):
    alias = normalize_alias(alias)
    uid = (await account.user).ID
    if not await save_alias(alias, uid):
        raise NeedCatchError(Lang.alias.conflict, alias=alias)
    await UniMessage(Lang.alias.saved(alias=alias)).finish()


@assign('TETRIO.alias.remove', default_available=False)
async def _(alias: str):
    alias = normalize_alias(alias)
    async with get_session() as session:
        entry = await session.get(TETRIOPlayerAlias, alias)
        if entry is None:
            raise NeedCatchError(Lang.alias.not_found, alias=alias)
        await session.delete(entry)
        await session.commit()
    await UniMessage(Lang.alias.removed(alias=alias)).finish()
