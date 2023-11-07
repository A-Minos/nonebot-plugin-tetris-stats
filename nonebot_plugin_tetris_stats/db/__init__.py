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
