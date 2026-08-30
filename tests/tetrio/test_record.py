from dataclasses import dataclass
from datetime import datetime, timezone
from json import dumps
from typing import TYPE_CHECKING, Literal, Protocol

import pytest
from yarl import URL

if TYPE_CHECKING:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordModeType, RecordType
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import Cache
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base.solo import Record as ApiRecord
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.records import Parameter
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.records.solo import (
        SoloSuccessModel as RecordsSoloSuccessModel,
    )
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.solo import (
        Record as SummaryRecord,
    )
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.solo import (
        SoloSuccessModel as SummariesSoloSuccessModel,
    )
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.user import User
    from nonebot_plugin_tetris_stats.utils.render.schemas.v2.tetrio.record.base import RecordRenderType

SELECTED_INDEX = 2
EXPECTED_CACHE_REQUESTS = 6
INDEX_AFTER_DEFAULT_PAGE = 26
API_PAGE_LIMIT = 100
CROSS_PAGE_INDEX = 125
OUT_OF_RANGE_INDEX = 101
EXPECTED_PAGE_REQUESTS = 2


@dataclass(frozen=True)
class RecordFlags:
    pb: bool = False
    oncepb: bool = False
    disputed: bool = False


DEFAULT_RECORD_FLAGS = RecordFlags()


class _RenderedRecord(Protocol):
    replay_id: str
    type: 'RecordRenderType'
    rank: int | None
    personal_rank: int | None


def _cache() -> 'Cache':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import Cache  # noqa: PLC0415

    return Cache(
        status='cached',
        cached_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        cached_until=datetime(2026, 8, 30, 0, 1, tzinfo=timezone.utc),
    )


def _record(
    mode: Literal['40l', 'blitz'],
    replay_id: str,
    order: int = 1,
    *,
    flags: RecordFlags = DEFAULT_RECORD_FLAGS,
) -> 'ApiRecord':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import (  # noqa: PLC0415
        AggregateStats,
        Clears,
        Finesse,
        Garbage,
        P,
    )
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base.solo import (  # noqa: PLC0415
        Record,
        Results,
        Stats,
    )

    return Record(
        _id=f'record-{replay_id}',
        replayid=replay_id,
        stub=False,
        gamemode=mode,
        pb=flags.pb,
        oncepb=flags.oncepb,
        ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        revolution=None,
        otherusers=[],
        leaderboards=[],
        results=Results(
            aggregatestats=AggregateStats(apm=0, pps=2.5, vsscore=0),
            stats=Stats(
                lines=40,
                level_lines=0,
                level_lines_needed=0,
                inputs=250,
                holds=10,
                score=100000,
                level=10,
                combo=0,
                topcombo=5,
                btb=0,
                topbtb=6,
                tspins=5,
                piecesplaced=100,
                clears=Clears(
                    singles=1,
                    doubles=2,
                    triples=3,
                    quads=4,
                    realtspins=5,
                    minitspins=3,
                    minitspinsingles=1,
                    tspinsingles=1,
                    minitspindoubles=2,
                    tspindoubles=2,
                    tspintriples=2,
                    tspinquads=0,
                    allclear=1,
                ),
                garbage=Garbage(sent=0, received=0, attack=None, cleared=0),
                kills=0,
                finesse=Finesse(combo=0, faults=2, perfectpieces=98),
                finaltime=40000,
            ),
            gameoverreason='completed',
        ),
        extras={},
        disputed=flags.disputed,
        p=P(pri=order, sec=0, ter=0),
    )


def _summary_record(record: 'ApiRecord') -> 'SummaryRecord':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.base import (  # noqa: PLC0415
        User as SummaryUser,
    )
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.solo import (  # noqa: PLC0415
        Record,
    )

    return Record(
        _id=record.id,
        replayid=record.replayid,
        stub=record.stub,
        gamemode=record.gamemode,
        pb=record.pb,
        oncepb=record.oncepb,
        ts=record.ts,
        revolution=record.revolution,
        otherusers=record.otherusers,
        leaderboards=record.leaderboards,
        results=record.results,
        extras=record.extras,
        disputed=record.disputed,
        p=record.p,
        user=SummaryUser(
            id='user-id',
            username='tester',
            avatar_revision=None,
            banner_revision=None,
            country=None,
            supporter=False,
        ),
    )


def _summary(record: 'SummaryRecord | None', rank: int = 9) -> 'SummariesSoloSuccessModel':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.solo import (  # noqa: PLC0415
        Data,
        SoloSuccessModel,
    )

    return SoloSuccessModel(
        success=True,
        cache=_cache(),
        data=Data(record=record, rank=rank, rank_local=rank),
    )


def _records(entries: list['ApiRecord']) -> 'RecordsSoloSuccessModel':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.records.solo import (  # noqa: PLC0415
        Data,
        SoloSuccessModel,
    )

    return SoloSuccessModel(success=True, cache=_cache(), data=Data(entries=entries))


class _FakePlayer:
    def __init__(self, summary_record: 'SummaryRecord | None', entries: list['ApiRecord'], rank: int = 9):
        from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.user import User  # noqa: PLC0415

        self.summary = _summary(summary_record, rank)
        self.entries = entries
        self.record_calls: list[tuple[RecordModeType, RecordType, Parameter | None]] = []
        self._user = User(ID='user-id', name='tester')

    @property
    async def user(self) -> 'User':
        return self._user

    @property
    async def sprint(self) -> 'SummariesSoloSuccessModel':
        return self.summary

    @property
    async def blitz(self) -> 'SummariesSoloSuccessModel':
        return self.summary

    @property
    async def avatar_revision(self) -> int | None:
        return None

    async def get_records(
        self,
        mode_type: 'RecordModeType',
        records_type: 'RecordType',
        *,
        parameter: 'Parameter | None' = None,
    ) -> 'RecordsSoloSuccessModel':
        from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.records import Parameter  # noqa: PLC0415

        self.record_calls.append((mode_type, records_type, parameter))
        request = parameter or Parameter()
        start = 0
        if request.after is not None:
            start = len(self.entries)
            for position, entry in enumerate(self.entries):
                if entry.p.to_prisecter() == request.after:
                    start = position + 1
                    break
        return _records(self.entries[start : start + request.limit])


@pytest.mark.parametrize('mode', ['--40l', '--blitz'])
def test_record_command_parses_stateless_selector_and_keeps_default(mode: str) -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordType  # noqa: PLC0415

    default = command.parse(f'tstats TETR.IO record tester {mode}')
    selected = command.parse(f'tstats TETR.IO record tester {mode} --type recent --index {SELECTED_INDEX}')

    assert default.matched  # noqa: S101
    assert 'record_type' not in default.all_matched_args  # noqa: S101
    assert 'index' not in default.all_matched_args  # noqa: S101
    assert selected.matched  # noqa: S101
    assert selected.all_matched_args['record_type'] is RecordType.Recent  # noqa: S101
    assert selected.all_matched_args['index'] == SELECTED_INDEX  # noqa: S101


@pytest.mark.asyncio
async def test_record_default_still_uses_summary_pb(monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.record import blitz, sprint  # noqa: PLC0415

    captured: list[_RenderedRecord] = []

    async def capture(data: _RenderedRecord) -> bytes:
        captured.append(data)
        return b'image'

    monkeypatch.setattr(sprint, 'render_image', capture)
    monkeypatch.setattr(blitz, 'render_image', capture)

    sprint_player = _FakePlayer(
        _summary_record(_record('40l', 'sprint-summary', flags=RecordFlags(pb=True))),
        [],
    )
    blitz_player = _FakePlayer(
        _summary_record(_record('blitz', 'blitz-summary', flags=RecordFlags(pb=True))),
        [],
    )
    assert await sprint.make_sprint_image(sprint_player) == b'image'  # noqa: S101
    assert await blitz.make_blitz_image(blitz_player) == b'image'  # noqa: S101

    assert sprint_player.record_calls == []  # noqa: S101
    assert blitz_player.record_calls == []  # noqa: S101
    assert [(item.replay_id, item.type, item.rank, item.personal_rank) for item in captured] == [  # noqa: S101
        ('sprint-summary', 'best', 9, 1),
        ('blitz-summary', 'best', 9, 1),
    ]


@pytest.mark.asyncio
async def test_sprint_top_entries_map_all_v2_record_types(monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import sprint  # noqa: PLC0415

    entries = [
        _record('40l', 'best', flags=RecordFlags(pb=True)),
        _record('40l', 'personal-best', flags=RecordFlags(oncepb=True)),
        _record('40l', 'recent'),
        _record('40l', 'disputed', flags=RecordFlags(pb=True, disputed=True)),
    ]
    player = _FakePlayer(None, entries)
    captured: list[_RenderedRecord] = []

    async def capture(data: _RenderedRecord) -> bytes:
        captured.append(data)
        return b'image'

    monkeypatch.setattr(sprint, 'render_image', capture)
    for index in range(1, len(entries) + 1):
        await sprint.make_sprint_image(player, RecordType.Top, index)

    assert [(item.replay_id, item.type, item.rank, item.personal_rank) for item in captured] == [  # noqa: S101
        ('best', 'best', None, 1),
        ('personal-best', 'personal_best', None, 2),
        ('recent', 'recent', None, 3),
        ('disputed', 'disputed', None, 4),
    ]


@pytest.mark.asyncio
async def test_blitz_recent_selection_does_not_treat_recency_as_personal_rank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordModeType, RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import blitz  # noqa: PLC0415

    player = _FakePlayer(
        None,
        [_record('blitz', 'recent'), _record('blitz', 'current-pb', flags=RecordFlags(pb=True))],
    )
    captured: list[_RenderedRecord] = []

    async def capture(data: _RenderedRecord) -> bytes:
        captured.append(data)
        return b'image'

    monkeypatch.setattr(blitz, 'render_image', capture)
    await blitz.make_blitz_image(player, RecordType.Recent, 1)
    await blitz.make_blitz_image(player, RecordType.Recent, 2)

    assert player.record_calls == [  # noqa: S101
        (RecordModeType.Blitz, RecordType.Recent, None),
        (RecordModeType.Blitz, RecordType.Recent, None),
    ]
    assert [(item.replay_id, item.type, item.personal_rank) for item in captured] == [  # noqa: S101
        ('recent', 'recent', None),
        ('current-pb', 'best', 1),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('entry_count', 'index'),
    [
        (0, 1),
        (1, 0),
        (1, 2),
    ],
)
async def test_record_selection_rejects_empty_and_non_1_based_indices(
    monkeypatch: pytest.MonkeyPatch,
    entry_count: int,
    index: int,
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import sprint  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.exception import RecordNotFoundError  # noqa: PLC0415

    entries = [_record('40l', f'record-{position}', order=position) for position in range(1, entry_count + 1)]

    async def unexpected_render(_: _RenderedRecord) -> bytes:
        pytest.fail('out-of-range records must not be rendered')

    monkeypatch.setattr(sprint, 'render_image', unexpected_render)
    with pytest.raises(RecordNotFoundError):
        await sprint.make_sprint_image(_FakePlayer(None, entries), RecordType.Top, index)


@pytest.mark.asyncio
async def test_record_index_26_expands_the_first_page() -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordModeType, RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import select_record  # noqa: PLC0415

    entries = [_record('40l', f'record-{index}', order=index) for index in range(1, INDEX_AFTER_DEFAULT_PAGE + 1)]
    player = _FakePlayer(None, entries)

    selected = await select_record(player, RecordModeType.Sprint, RecordType.Top, INDEX_AFTER_DEFAULT_PAGE)

    assert selected is not None  # noqa: S101
    assert selected.record.replayid == 'record-26'  # noqa: S101
    assert len(player.record_calls) == 1  # noqa: S101
    parameter = player.record_calls[0][2]
    assert parameter is not None  # noqa: S101
    assert parameter.after is None  # noqa: S101
    assert parameter.limit == INDEX_AFTER_DEFAULT_PAGE  # noqa: S101


@pytest.mark.asyncio
async def test_record_index_paginates_past_100_entries() -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordModeType, RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import select_record  # noqa: PLC0415

    entries = [_record('40l', f'record-{index}', order=index) for index in range(1, CROSS_PAGE_INDEX + 1)]
    player = _FakePlayer(None, entries)

    selected = await select_record(player, RecordModeType.Sprint, RecordType.Top, CROSS_PAGE_INDEX)

    assert selected is not None  # noqa: S101
    assert selected.record.replayid == 'record-125'  # noqa: S101
    assert len(player.record_calls) == EXPECTED_PAGE_REQUESTS  # noqa: S101
    first_page = player.record_calls[0][2]
    second_page = player.record_calls[1][2]
    assert first_page is not None  # noqa: S101
    assert first_page.after is None  # noqa: S101
    assert first_page.limit == API_PAGE_LIMIT  # noqa: S101
    assert second_page is not None  # noqa: S101
    assert second_page.after == entries[API_PAGE_LIMIT - 1].p.to_prisecter()  # noqa: S101
    assert second_page.limit == CROSS_PAGE_INDEX - API_PAGE_LIMIT  # noqa: S101


@pytest.mark.asyncio
async def test_record_index_returns_none_only_after_the_last_page_is_exhausted() -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordModeType, RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import select_record  # noqa: PLC0415

    entries = [_record('40l', f'record-{index}', order=index) for index in range(1, API_PAGE_LIMIT + 1)]
    player = _FakePlayer(None, entries)

    selected = await select_record(player, RecordModeType.Sprint, RecordType.Top, OUT_OF_RANGE_INDEX)

    assert selected is None  # noqa: S101
    assert len(player.record_calls) == EXPECTED_PAGE_REQUESTS  # noqa: S101
    last_page = player.record_calls[1][2]
    assert last_page is not None  # noqa: S101
    assert last_page.after == entries[-1].p.to_prisecter()  # noqa: S101
    assert last_page.limit == 1  # noqa: S101


@pytest.mark.asyncio
async def test_player_records_cache_isolated_by_mode_type_and_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api import player as player_module  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.models import TETRIOHistoricalData  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import (  # noqa: PLC0415
        Player,
        RecordModeType,
        RecordType,
    )
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.records import Parameter  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.user import User  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.typedefs import Prisecter  # noqa: PLC0415

    requested: list[str] = []

    async def fake_get(url: URL) -> bytes:
        requested.append(str(url))
        return dumps(
            {
                'success': True,
                'cache': {
                    'status': 'cached',
                    'cached_at': '2026-08-30T00:00:00Z',
                    'cached_until': '2026-08-30T00:01:00Z',
                },
                'data': {'entries': []},
            }
        ).encode()

    async def fake_add(_: TETRIOHistoricalData) -> None:
        return None

    async def fake_user(_: Player) -> User:
        return User(ID='user-id', name='tester')

    monkeypatch.setattr(player_module.Cache, 'get', fake_get)
    monkeypatch.setattr(player_module, 'anti_duplicate_add', fake_add)
    monkeypatch.setattr(Player, 'user', property(fake_user))

    player = Player(user_id='user-id', trust=True)
    top_limit_one = await player.get_records(RecordModeType.Sprint, RecordType.Top, parameter=Parameter(limit=1))
    repeated = await player.get_records(RecordModeType.Sprint, RecordType.Top, parameter=Parameter(limit=1))
    top_limit_two = await player.get_records(RecordModeType.Sprint, RecordType.Top, parameter=Parameter(limit=2))
    recent = await player.get_records(RecordModeType.Sprint, RecordType.Recent)
    blitz = await player.get_records(RecordModeType.Blitz, RecordType.Top)
    first_page = await player.get_records(
        RecordModeType.Sprint,
        RecordType.Top,
        parameter=Parameter(after=Prisecter('100:0:0'), limit=100),
    )
    repeated_first_page = await player.get_records(
        RecordModeType.Sprint,
        RecordType.Top,
        parameter=Parameter(after=Prisecter('100:0:0'), limit=100),
    )
    second_page = await player.get_records(
        RecordModeType.Sprint,
        RecordType.Top,
        parameter=Parameter(after=Prisecter('200:0:0'), limit=100),
    )

    assert repeated is top_limit_one  # noqa: S101
    assert top_limit_two is not top_limit_one  # noqa: S101
    assert recent is not top_limit_one  # noqa: S101
    assert blitz is not top_limit_one  # noqa: S101
    assert repeated_first_page is first_page  # noqa: S101
    assert second_page is not first_page  # noqa: S101
    assert len(requested) == EXPECTED_CACHE_REQUESTS  # noqa: S101
    assert len(set(requested)) == EXPECTED_CACHE_REQUESTS  # noqa: S101
