# ruff: noqa: PLC0415
# TETR.IO schema imports stay inside tests so pytest collection does not import
# the plugin before NoneBot fixtures initialize it.
from typing import Any

ZEN_SCORE = 123


def _cache_payload() -> dict[str, str]:
    return {
        'status': 'cached',
        'cached_at': '2026-07-08T00:00:00Z',
        'cached_until': '2026-07-08T00:01:00Z',
    }


def _s1_past_payload() -> dict[str, Any]:
    return {
        'season': '1',
        'username': 'alice',
        'country': 'JP',
        'placement': 12,
        'gamesplayed': 40,
        'gameswon': 25,
        'glicko': 1500.0,
        'gxe': 0.6,
        'tr': 12345.67,
        'rd': 55.0,
        'rank': 's',
        'bestrank': 's+',
        'ranked': True,
        'apm': 42.5,
        'pps': 2.1,
        'vs': 88.0,
    }


def _rated_league_payload() -> dict[str, Any]:
    return {
        'success': True,
        'cache': _cache_payload(),
        'data': {
            'decaying': False,
            'past': {'1': _s1_past_payload()},
            'gamesplayed': 42,
            'gameswon': 28,
            'glicko': 1500.0,
            'rd': 50.0,
            'gxe': 0.61,
            'tr': 12345.67,
            'rank': 'x+',
            'bestrank': 'x+',
            'standing': 100,
            'apm': 42.5,
            'pps': 2.1,
            'vs': 88.0,
            'standing_local': 10,
            'prev_rank': 's-',
            'prev_at': 12000,
            'next_rank': 'ss',
            'next_at': 13000,
            'percentile': 0.9,
            'percentile_rank': 's',
        },
    }


def test_tetrio_failed_model_accepts_structured_error_msg() -> None:
    from nonebot.compat import type_validate_python

    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import FailedModel

    model = type_validate_python(FailedModel, {'success': False, 'error': {'msg': 'rate limited'}})

    assert model.success is False  # noqa: S101
    assert model.error.msg == 'rate limited'  # noqa: S101
    assert str(model.error) == 'rate limited'  # noqa: S101


def test_tetrio_league_separates_s1_past_from_current_s2() -> None:
    from nonebot.compat import type_validate_python

    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.league import LeagueSuccessModel, RatedData

    model = type_validate_python(LeagueSuccessModel, _rated_league_payload())

    assert isinstance(model.data, RatedData)  # noqa: S101
    assert model.data.rank == 'x+'  # noqa: S101
    assert model.data.past.first is not None  # noqa: S101
    assert model.data.past.first.rank == 's'  # noqa: S101
    assert model.data.past.first.bestrank == 's+'  # noqa: S101


def test_tetrio_summaries_user_accepts_boolean_supporter() -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.base import User

    user = User.model_validate(
        {
            'id': 'user-id',
            'username': 'alice',
            'avatar_revision': None,
            'banner_revision': None,
            'country': None,
            'supporter': True,
        }
    )

    assert user.supporter is True  # noqa: S101


def test_tetrio_zen_summary_preserves_integer_score() -> None:
    from nonebot.compat import type_validate_python

    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.zen import ZenSuccessModel

    model = type_validate_python(
        ZenSuccessModel,
        {
            'success': True,
            'cache': _cache_payload(),
            'data': {
                'level': 99,
                'score': ZEN_SCORE,
            },
        },
    )

    assert isinstance(model.data.score, int)  # noqa: S101
    assert model.data.score == ZEN_SCORE  # noqa: S101
