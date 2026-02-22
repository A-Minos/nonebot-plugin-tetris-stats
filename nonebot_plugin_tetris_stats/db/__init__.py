from asyncio import Lock
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import TYPE_CHECKING, Literal, TypeVar, overload

from nonebot.exception import FinishedException
from nonebot.log import logger
from nonebot_plugin_orm import AsyncSession, get_session
from nonebot_plugin_user import User
from sqlalchemy import select

from ..utils.duration import DEFAULT_COMPARE_DELTA
from ..utils.typedefs import AllCommandType, BaseCommandType, GameType, TETRIOCommandType
from .models import Bind, TriggerHistoricalDataV2

UTC = timezone.utc

if TYPE_CHECKING:
    from ..games.tetrio.api.models import TETRIOHistoricalData
    from ..games.tetrio.models import TETRIOUserConfig
    from ..games.top.api.models import TOPHistoricalData
    from ..games.top.models import TOPUserConfig
    from ..games.tos.api.models import TOSHistoricalData
    from ..games.tos.models import TOSUserConfig


class BindStatus(Enum):
    SUCCESS = auto()
    UPDATE = auto()


async def query_bind_info(
    session: AsyncSession,
    user: User,
    game_platform: GameType,
) -> Bind | None:
    return (
        await session.scalars(select(Bind).where(Bind.user_id == user.id).where(Bind.game_platform == game_platform))
    ).one_or_none()


async def create_or_update_bind(
    session: AsyncSession,
    user: User,
    game_platform: GameType,
    game_account: str,
    *,
    verify: bool = False,
) -> BindStatus:
    bind = await query_bind_info(
        session=session,
        user=user,
        game_platform=game_platform,
    )
    if bind is None:
        bind = Bind(
            user_id=user.id,
            game_platform=game_platform,
            game_account=game_account,
            verify=verify,
        )
        session.add(bind)
        status = BindStatus.SUCCESS
    else:
        bind.game_account = game_account
        bind.verify = verify
        status = BindStatus.UPDATE
    await session.commit()
    return status


async def remove_bind(
    session: AsyncSession,
    user: User,
    game_platform: GameType,
) -> bool:
    bind = await query_bind_info(
        session=session,
        user=user,
        game_platform=game_platform,
    )
    if bind is not None:
        await session.delete(bind)
        await session.commit()
        return True
    return False


T_HistoricalData = TypeVar('T_HistoricalData', 'TETRIOHistoricalData', 'TOPHistoricalData', 'TOSHistoricalData')

lock = Lock()


async def anti_duplicate_add(model: T_HistoricalData) -> None:
    async with lock, get_session() as session:
        result = (
            await session.scalars(
                select(cls := model.__class__)
                .where(cls.update_time == model.update_time)
                .where(cls.user_unique_identifier == model.user_unique_identifier)
                .where(cls.api_type == model.api_type)
            )
        ).all()
        if result:
            for i in result:
                if i.data == model.data:
                    logger.debug('Anti duplicate successfully')
                    return
        session.add(model)
        await session.commit()


T_CONFIG = TypeVar('T_CONFIG', 'TETRIOUserConfig', 'TOPUserConfig', 'TOSUserConfig')


async def resolve_compare_delta(
    config: type[T_CONFIG], session: AsyncSession, user_id: int, compare: timedelta | None
) -> timedelta:
    return (
        compare
        or await session.scalar(select(config.compare_delta).where(config.id == user_id))
        or DEFAULT_COMPARE_DELTA
    )


@asynccontextmanager
@overload
async def trigger(
    session_persist_id: int,
    game_platform: Literal['IO'],
    command_type: TETRIOCommandType,
    command_args: list[str],
) -> AsyncGenerator:
    yield


@asynccontextmanager
@overload
async def trigger(
    session_persist_id: int,
    game_platform: GameType,
    command_type: BaseCommandType,
    command_args: list[str],
) -> AsyncGenerator:
    yield


@asynccontextmanager
async def trigger(
    session_persist_id: int,
    game_platform: GameType,
    command_type: AllCommandType,
    command_args: list[str],
) -> AsyncGenerator:
    trigger_time = datetime.now(UTC)
    try:
        yield
    except FinishedException:
        async with get_session() as session:
            session.add(
                TriggerHistoricalDataV2(
                    trigger_time=trigger_time,
                    session_persist_id=session_persist_id,
                    game_platform=game_platform,
                    command_type=command_type,
                    command_args=command_args,
                    finish_time=datetime.now(UTC),
                )
            )
            await session.commit()
        raise
