from collections.abc import AsyncIterator, Iterator
from hashlib import md5
from typing import TYPE_CHECKING

import pytest
from nonebot.compat import PYDANTIC_V2
from pydantic import BaseModel
from tarina.lang import lang  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from nonebot_plugin_tetris_stats.utils.render.schemas.v2.tetrio.user.list import List

MASKED_UID = '0123456789abcdef01234567'
NORMAL_UID = 'fedcba9876543210fedcba98'


@pytest.fixture(autouse=True)
def chinese_locale() -> Iterator[None]:
    previous = lang.current
    lang.select('zh-CN')
    yield
    lang.select(previous)


@pytest.fixture
async def mask_database() -> AsyncIterator[None]:
    from nonebot_plugin_orm import get_session  # noqa: PLC0415
    from sqlalchemy import delete  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games.tetrio.models import TETRIODisplayMask  # noqa: PLC0415

    async with get_session() as session:
        connection = await session.connection()
        await connection.run_sync(
            lambda conn: TETRIODisplayMask.metadata.create_all(conn, [TETRIODisplayMask.__table__])
        )
        await session.execute(delete(TETRIODisplayMask))
        session.add_all(
            [TETRIODisplayMask(uid=MASKED_UID, field='name'), TETRIODisplayMask(uid=MASKED_UID, field='country')]
        )
        await session.commit()
    yield
    async with get_session() as session:
        await session.execute(delete(TETRIODisplayMask))
        await session.commit()


def dump(model: BaseModel) -> str:
    return model.model_dump_json() if PYDANTIC_V2 else model.json()


def make_list(*uids: str) -> 'List':
    from nonebot_plugin_tetris_stats.utils.render.schemas.v2.tetrio.user.list import (  # noqa: PLC0415
        Data,
        List,
        TetraLeague,
        User,
    )

    return List(
        show_index=True,
        data=[
            Data(
                user=User(
                    id=uid,
                    name=uid.upper(),
                    avatar=f'https://tetr.io/user-content/avatars/{uid}.jpg',
                    country='CN',
                    xp=1.0,
                ),
                tetra_league=TetraLeague(
                    pps=1, apm=1, apl=1, vs=1, adpl=1, rank='x', tr=1, glicko=1, rd=1, decaying=False
                ),
            )
            for uid in uids
        ],
        lang='zh-CN',
    )


def test_iter_players_matches_by_type_only() -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.mask import iter_players  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.v2.tetrio.user.info import Badge  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.v2.tetrio.user.list import List  # noqa: PLC0415

    class Wrapper(BaseModel):
        badges: list[Badge]
        players: List

    wrapper = Wrapper(
        badges=[Badge(id=MASKED_UID, description='', group=None, receive_at=None)],
        players=make_list(MASKED_UID, NORMAL_UID),
    )

    assert [player.id for player in iter_players(wrapper)] == [MASKED_UID, NORMAL_UID]  # noqa: S101


def test_apply_mask_replaces_selected_fields_only() -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.mask import apply_mask  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.base import Avatar  # noqa: PLC0415

    user = make_list(MASKED_UID).data[0].user
    apply_mask(user, {'avatar', 'bio'})

    assert user.avatar == Avatar(type='identicon', hash=md5(MASKED_UID.encode()).hexdigest())  # noqa: S101, S324
    assert user.name == MASKED_UID.upper()  # noqa: S101
    assert user.country == 'CN'  # noqa: S101

    apply_mask(user, {'name', 'country'})

    assert user.name == '已屏蔽'  # noqa: S101
    assert user.country is None  # noqa: S101
    assert user.xp == 1.0  # noqa: S101
    assert user.id == MASKED_UID  # noqa: S101


def test_display_name() -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.mask import display_name  # noqa: PLC0415

    assert display_name('USER', {'avatar'}) == 'USER'  # noqa: S101
    assert display_name('USER', {'name'}) == '已屏蔽'  # noqa: S101


def test_tetrio_people_keeps_id_out_of_json() -> None:
    from nonebot_plugin_tetris_stats.utils.render.schemas.base import People, TETRIOPeople  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.bind import Bind  # noqa: PLC0415

    bind = Bind(
        platform='TETR.IO',
        type='success',
        user=TETRIOPeople(id=MASKED_UID, name='USER', avatar='avatar'),
        bot=People(name='BOT', avatar='avatar'),
        prompt='',
        lang='zh-CN',
    )

    assert isinstance(bind.user, TETRIOPeople)  # noqa: S101
    assert MASKED_UID not in dump(bind)  # noqa: S101


@pytest.mark.usefixtures('mask_database')
async def test_pre_render_hook_masks_listed_players() -> None:
    from nonebot_plugin_tetris_stats.utils.render import pre_render_hooks  # noqa: PLC0415

    data = make_list(MASKED_UID, NORMAL_UID)
    for hook in pre_render_hooks:
        await hook(data)

    masked, normal = (item.user for item in data.data)
    assert masked.name == '已屏蔽'  # noqa: S101
    assert masked.country is None  # noqa: S101
    assert masked.avatar == f'https://tetr.io/user-content/avatars/{MASKED_UID}.jpg'  # noqa: S101
    assert normal.name == NORMAL_UID.upper()  # noqa: S101
    assert normal.country == 'CN'  # noqa: S101
