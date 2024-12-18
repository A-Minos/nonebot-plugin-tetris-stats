from typing import Literal, overload
from uuid import UUID

from nonebot import __version__ as __nonebot_version__
from nonebot.compat import type_validate_json
from yarl import URL

from ....utils.exception import RequestError
from ....version import __version__
from ..constant import BASE_URL
from .cache import Cache
from .schemas.base import FailedModel
from .schemas.leaderboards import Parameter
from .schemas.leaderboards.by import By, BySuccessModel
from .schemas.leaderboards.solo import Solo, SoloSuccessModel
from .schemas.leaderboards.zenith import Zenith, ZenithSuccessModel


async def by(
    by_type: Literal['league', 'xp', 'ar'], parameter: Parameter, x_session_id: UUID | None = None
) -> BySuccessModel:
    model: By = type_validate_json(
        By,  # type: ignore[arg-type]
        await get(
            BASE_URL / f'users/by/{by_type}',
            parameter,
            {
                'X-Session-ID': str(x_session_id),
                'User-Agent': f'nonebot-plugin-tetris-stats/{__version__} (Windows NT 10.0; Win64; x64) NoneBot2/{__nonebot_version__}',
            }
            if x_session_id is not None
            else None,
        ),
    )
    if isinstance(model, FailedModel):
        msg = f'排行榜信息请求错误:\n{model.error}'
        raise RequestError(msg)
    return model


@overload
async def records(
    records_type: Literal['40l', 'blitz'],
    scope: str = '_global',
    revolution_id: str | None = None,
    *,
    parameter: Parameter,
) -> SoloSuccessModel: ...


@overload
async def records(
    records_type: Literal['zenith', 'zenithex'],
    scope: str = '_global',
    revolution_id: str | None = None,
    *,
    parameter: Parameter,
) -> ZenithSuccessModel: ...


async def records(
    records_type: Literal['40l', 'blitz', 'zenith', 'zenithex'],
    scope: str = '_global',
    revolution_id: str | None = None,
    *,
    parameter: Parameter,
) -> SoloSuccessModel | ZenithSuccessModel:
    model: Solo | Zenith
    match records_type:
        case '40l' | 'blitz':
            model = type_validate_json(
                Solo,  # type: ignore[arg-type]
                await get(
                    BASE_URL / 'records' / f'{records_type}{scope}{revolution_id if revolution_id is not None else ""}',
                    parameter,
                ),
            )
        case 'zenith' | 'zenithex':
            model = type_validate_json(
                Zenith,  # type: ignore[arg-type]
                await get(
                    BASE_URL / 'records' / f'{records_type}{scope}{revolution_id if revolution_id is not None else ""}',
                    parameter,
                ),
            )
        case _:
            msg = f'records_type: {records_type} is not supported'
            raise ValueError(msg)
    if isinstance(model, FailedModel):
        msg = f'排行榜信息请求错误:\n{model.error}'  # type: ignore[attr-defined]
        raise RequestError(msg)
    return model


async def get(url: URL, parameter: Parameter, extra_headers: dict | None = None) -> bytes:
    return await Cache.get(url % parameter.to_params(), extra_headers)
