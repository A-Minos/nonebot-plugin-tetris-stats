import os

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter
from nonebug import NONEBOT_INIT_KWARGS, NONEBOT_START_LIFESPAN  # type: ignore[import-untyped]

os.environ['ENVIRONMENT'] = 'test'


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {'log_level': 'DEBUG'}
    config.stash[NONEBOT_START_LIFESPAN] = False


@pytest.fixture(scope='session', autouse=True)
async def after_nonebot_init(after_nonebot_init: None) -> None:  # noqa: ARG001
    driver = nonebot.get_driver()
    driver.register_adapter(OnebotV11Adapter)

    nonebot.load_from_toml('pyproject.toml')
