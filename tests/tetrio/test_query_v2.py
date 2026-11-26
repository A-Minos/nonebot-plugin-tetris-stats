from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from nonebot_plugin_tetris_stats.games.tetrio.api import Player


@pytest.mark.asyncio
@pytest.mark.parametrize('names', [[], ['older_name', 'oldest_name']])
async def test_v2_query_passes_former_names_and_respects_name_mask(
    monkeypatch: pytest.MonkeyPatch, names: list[str]
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.league import InvalidData  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.user_info import Data  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.mask import apply_mask  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.query import v2  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.v2.tetrio.user.info import Info  # noqa: PLC0415

    uid = '0123456789abcdef01234567'
    data = Data(
        _id=uid,
        username='current_name',
        role='user',
        badges=[],
        xp=0,
        gamesplayed=0,
        gameswon=0,
        gametime=0,
        supporter_tier=0,
        connections={},
        achievements=[],
        ar=0,
        ar_counts={},
        oldusernames=[{'username': name, 'ts': '2026-01-01T00:00:00Z'} for name in names],
    )

    async def resolved(value: object) -> object:
        return value

    async def get_summaries(mode: str) -> SimpleNamespace:
        if mode == 'achievements':
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=SimpleNamespace(record=None, best=SimpleNamespace(record=None)))

    captured: list[Info] = []

    async def capture(info: Info) -> bytes:
        captured.append(info)
        return b'png'

    monkeypatch.setattr(v2, 'render_image', capture)
    monkeypatch.setattr(v2, 'get_lang', lambda: 'zh-CN')
    monkeypatch.setattr(v2, 'get_self_netloc', lambda: 'localhost')
    monkeypatch.setattr(v2, 'flow_to_history', lambda *_: None)
    player = cast(
        'Player',
        SimpleNamespace(
            user=resolved(SimpleNamespace(ID=uid, name=data.username)),
            get_info=lambda: resolved(SimpleNamespace(data=data)),
            league=resolved(SimpleNamespace(data=InvalidData())),
            sprint=resolved(SimpleNamespace(data=SimpleNamespace(record=None))),
            blitz=resolved(SimpleNamespace(data=SimpleNamespace(record=None))),
            zen=resolved(SimpleNamespace(data=SimpleNamespace(level=0, score=0))),
            avatar_revision=resolved(None),
            banner_revision=resolved(None),
            get_leagueflow=lambda: resolved(None),
            get_summaries=get_summaries,
        ),
    )

    assert await v2.make_query_image_v2(player) == b'png'  # noqa: S101
    (info,) = captured
    assert info.user.name == 'CURRENT_NAME'  # noqa: S101
    assert info.user.old_names == names  # noqa: S101
    apply_mask(info.user, {'avatar'})
    assert info.user.old_names == names  # noqa: S101
    apply_mask(info.user, {'name'})
    assert info.user.old_names == []  # noqa: S101
