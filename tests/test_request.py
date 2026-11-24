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
