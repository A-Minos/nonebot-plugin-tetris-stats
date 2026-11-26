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


def test_avatar_requests_do_not_share_the_api_rate_limit() -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.cache import request as api_request
    from nonebot_plugin_tetris_stats.utils.host import resource_request

    assert getattr(api_request.request, '__wrapped__', None) is not None  # noqa: S101  # API 请求被 limit 包了一层
    assert resource_request is not api_request  # noqa: S101
    assert not hasattr(resource_request.request, '__wrapped__')  # noqa: S101


@pytest.mark.asyncio
@pytest.mark.parametrize('error_type', ['ConnectError', 'ConnectTimeout', 'ReadTimeout', 'RemoteProtocolError'])
async def test_httpx_transport_errors_are_reported_by_kind(error_type: str) -> None:
    import httpx
    from yarl import URL

    from nonebot_plugin_tetris_stats.utils import request as request_module
    from nonebot_plugin_tetris_stats.utils.exception import RequestError

    original = getattr(httpx, error_type)('')

    def fail(_request: httpx.Request) -> httpx.Response:
        raise original

    request = request_module.Request(proxy=None)
    await request.client.aclose()
    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
        request.client = client
        with pytest.raises(RequestError) as error:
            await request.request(URL('https://example.com'))

    assert error.value.__cause__ is original  # noqa: S101
    if error_type == 'RemoteProtocolError':
        assert error.value.render('en-US') == "Request error\nRemoteProtocolError('')"  # noqa: S101
    else:
        assert error.value.render('zh-CN') == '暂时连不上数据源，请稍后重试。'  # noqa: RUF001, S101
        assert error.value.render('en-US') == 'Could not reach the data source. Please try again later.'  # noqa: S101


@pytest.mark.asyncio
async def test_http_status_still_selects_failover_endpoint() -> None:
    import httpx
    from yarl import URL

    from nonebot_plugin_tetris_stats.utils import request as request_module

    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        if request.url.host == 'primary.example.com':
            return httpx.Response(503, text='Unavailable')
        return httpx.Response(200, content=b'{}')

    request = request_module.Request(proxy=None)
    await request.client.aclose()
    urls = [URL('https://primary.example.com'), URL('https://fallback.example.com')]
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        request.client = client
        result = await request.failover_request(urls, failover_code=(503,), failover_exc=())

    assert result == b'{}'  # noqa: S101
    assert calls == ['primary.example.com', 'fallback.example.com']  # noqa: S101
