# ruff: noqa: PLC0415
from pathlib import Path

import pytest


def test_anti_cloudflare_starts_with_an_empty_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats.utils import request as request_module

    monkeypatch.setattr(request_module, 'CACHE_PATH', tmp_path)

    anti_cloudflare = request_module.AntiCloudflare('example.com')

    assert anti_cloudflare.headers is None  # noqa: S101
    assert anti_cloudflare.cookies is None  # noqa: S101
    assert (tmp_path / 'example.com_cloudflare_cache.json').is_file()  # noqa: S101


@pytest.mark.asyncio
async def test_extra_headers_do_not_leak_into_the_cloudflare_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from yarl import URL

    from nonebot_plugin_tetris_stats.utils import request as request_module

    monkeypatch.setattr(request_module, 'CACHE_PATH', tmp_path)

    class FakeResponse:
        status_code = 200
        content = b'{}'
        text = '{}'

    sent_urls: list[str] = []
    sent_cookies: list[object] = []
    sent_headers: dict[str, str] = {}

    request = request_module.Request(proxy=None)
    try:
        anti_cloudflare = request_module.AntiCloudflare('example.com')
        anti_cloudflare.headers = {'X-Cache': '1'}
        request.anti_cloudflares['example.com'] = anti_cloudflare

        async def fake_get(url: str, cookies: object = None, headers: dict[str, str] | None = None) -> FakeResponse:
            sent_urls.append(url)
            sent_cookies.append(cookies)
            sent_headers.update(headers or {})
            return FakeResponse()

        monkeypatch.setattr(request.client, 'get', fake_get)

        await request.request(URL('https://example.com/'), {'X-Extra': '2'}, is_json=False)
    finally:
        await request.client.aclose()

    assert sent_urls == ['https://example.com/']  # noqa: S101
    assert sent_cookies == [None]  # noqa: S101
    assert {k: v for k, v in sent_headers.items() if k != 'User-Agent'} == {'X-Cache': '1', 'X-Extra': '2'}  # noqa: S101
    assert 'User-Agent' in sent_headers  # noqa: S101
    assert anti_cloudflare.headers == {'X-Cache': '1'}  # noqa: S101
