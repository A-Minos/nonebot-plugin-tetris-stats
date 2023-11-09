from nonebot_plugin_orm import AsyncSession
from sqlalchemy import select

from ..utils.typing import GameType
from .models import Bind


async def query_bind_info(
    session: AsyncSession,
    chat_platform: str,
    chat_account: str,
    game_platform: GameType,
) -> Bind | None:
    return (
        await session.scalars(
            select(Bind)
            .where(Bind.chat_platform == chat_platform)
            .where(Bind.chat_account == chat_account)
            .where(Bind.game_platform == game_platform)
        )
    ).one_or_none()


async def create_or_update_bind(
    session: AsyncSession,
    chat_platform: str,
    chat_account: str,
    game_platform: GameType,
    game_account: str,
) -> str:
    bind = await query_bind_info(
        session=session,
        chat_platform=chat_platform,
        chat_account=chat_account,
        game_platform=game_platform,
    )
    if bind is None:
        bind = Bind(
            chat_platform=chat_platform,
            chat_account=chat_account,
            game_platform=game_platform,
            game_account=game_account,
        )
        session.add(bind)
        message = '绑定成功'
    else:
        bind.game_account = game_account
        message = '更新绑定成功'
    await session.commit()
    return message
