import pytest


async def test_get_records_uses_enum_values_in_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import (  # noqa: PLC0415
        Cache,
        Player,
        RecordModeType,
        RecordType,
    )

    class RequestInterceptedError(Exception):
        pass

    async def intercept_request(url: object) -> bytes:
        if not str(url).endswith('/users/test-user/records/blitz/top'):
            pytest.fail(f'unexpected records URL: {url}')
        raise RequestInterceptedError

    monkeypatch.setattr(Cache, 'get', intercept_request)

    with pytest.raises(RequestInterceptedError):
        await Player(user_id='test-user', trust=True).get_records(RecordModeType.Blitz, RecordType.Top)
