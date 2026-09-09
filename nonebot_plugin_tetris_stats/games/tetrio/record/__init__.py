from typing import NamedTuple, Protocol

from arclet.alconna import Arg
from nonebot_plugin_alconna import Args, At, Option, Subcommand

from ....utils.render.schemas.v2.tetrio.record.base import RecordRenderType
from ....utils.typedefs import Me
from .. import command as base_command
from .. import get_player
from ..api.player import RecordModeType, RecordType
from ..api.schemas.base.solo import Record
from ..api.schemas.records import DEFAULT_RECORD_LIMIT, MAX_RECORD_LIMIT, Parameter
from ..api.schemas.records.solo import SoloSuccessModel as RecordsSoloSuccessModel
from ..api.schemas.summaries.solo import SoloSuccessModel as SummariesSoloSuccessModel
from ..api.schemas.user import User


class RecordSource(Protocol):
    @property
    async def user(self) -> User: ...

    @property
    async def sprint(self) -> SummariesSoloSuccessModel: ...

    @property
    async def blitz(self) -> SummariesSoloSuccessModel: ...

    @property
    async def avatar_revision(self) -> int | None: ...

    async def get_records(
        self,
        mode_type: RecordModeType,
        records_type: RecordType,
        *,
        parameter: Parameter | None = None,
    ) -> RecordsSoloSuccessModel: ...


class SelectedRecord(NamedTuple):
    record: Record
    type: RecordRenderType
    rank: int | None
    personal_rank: int | None


def parse_record_type(value: str) -> RecordType:
    return RecordType(value)


command = Subcommand(
    'record',
    Args(
        Arg(
            'who',
            At | Me | get_player,
            notice='@想要查询的人 / 自己 / TETR.IO 用户名 / ID',
        ),
    ),
    Option('--type', Arg('record_type', parse_record_type)),
    Option('--index', Arg('index', int)),
)


def get_command_args(mode: str, record_type: RecordType | None, index: int | None) -> list[str]:
    args = [mode]
    if record_type is not None:
        args.append(f'--type {record_type.value}')
    if index is not None:
        args.append(f'--index {index}')
    return args


def _get_render_type(record: Record) -> RecordRenderType:
    if record.disputed:
        return 'disputed'
    if record.pb:
        return 'best'
    if record.oncepb:
        return 'personal_best'
    return 'recent'


async def select_record(
    player: RecordSource,
    mode_type: RecordModeType,
    record_type: RecordType | None,
    index: int | None,
) -> SelectedRecord | None:
    if record_type is None and index is None:
        summary = await (player.sprint if mode_type is RecordModeType.Sprint else player.blitz)
        if summary.data.record is None:
            return None
        return SelectedRecord(summary.data.record, 'best', summary.data.rank, 1)

    record_type = record_type or RecordType.Top
    selected_index = 1 if index is None else index
    if selected_index < 1:
        return None

    remaining = selected_index
    parameter = None if remaining <= DEFAULT_RECORD_LIMIT else Parameter(limit=min(remaining, MAX_RECORD_LIMIT))
    while True:
        entries = (await player.get_records(mode_type, record_type, parameter=parameter)).data.entries
        if remaining <= len(entries):
            record = entries[remaining - 1]
            break

        requested_limit = parameter.limit if parameter is not None else DEFAULT_RECORD_LIMIT
        if len(entries) < requested_limit:
            return None

        remaining -= len(entries)
        parameter = Parameter(
            after=entries[-1].p.to_prisecter(),
            limit=min(remaining, MAX_RECORD_LIMIT),
        )

    personal_rank = selected_index if record_type is not RecordType.Recent else (1 if record.pb else None)
    return SelectedRecord(record, _get_render_type(record), None, personal_rank)


from . import blitz, sprint  # noqa: E402

base_command.add(command)

__all__ = [
    'blitz',
    'sprint',
]
