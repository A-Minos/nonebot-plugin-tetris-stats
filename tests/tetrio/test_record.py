from dataclasses import dataclass
from datetime import UTC, datetime
from json import dumps, loads
from typing import TYPE_CHECKING, Literal, Protocol

import pytest
from yarl import URL

if TYPE_CHECKING:
    from nonebot_plugin_tetris_stats.games.tetrio.api.models import TETRIOHistoricalData
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import Player
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import Cache
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base.solo import Record as ApiRecord
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.records.solo import (
        SoloSuccessModel as RecordsSoloSuccessModel,
    )
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.solo import (
        Record as SummaryRecord,
    )
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.solo import (
        SoloSuccessModel as SummariesSoloSuccessModel,
    )
    from nonebot_plugin_tetris_stats.utils.render.schemas.v2.tetrio.record.base import RecordQuery

SELECTED_INDEX = 2
EXPECTED_CACHE_REQUESTS = 9
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
    query: 'RecordQuery'
    global_rank: int | None
    country_rank: int | None
    personal_best: Literal['current', 'former'] | None
    disputed: bool

    def json(self, *, by_alias: bool = False) -> str: ...


def _cache() -> 'Cache':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import Cache  # noqa: PLC0415

    return Cache(
        status='cached',
        cached_at=datetime(2026, 8, 30, tzinfo=UTC),
        cached_until=datetime(2026, 8, 30, 0, 1, tzinfo=UTC),
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
        ts=datetime(2026, 8, 30, tzinfo=UTC),
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
        p=P(pri=-order, sec=0, ter=0),
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


def _summary(record: 'SummaryRecord | None', rank: int = 9, rank_local: int = 9) -> 'SummariesSoloSuccessModel':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.solo import (  # noqa: PLC0415
        Data,
        SoloSuccessModel,
    )

    return SoloSuccessModel(
        success=True,
        cache=_cache(),
        data=Data(record=record, rank=rank, rank_local=rank_local),
    )


def _records(entries: list['ApiRecord']) -> 'RecordsSoloSuccessModel':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.records.solo import (  # noqa: PLC0415
        Data,
        SoloSuccessModel,
    )

    return SoloSuccessModel(success=True, cache=_cache(), data=Data(entries=entries))


@dataclass
class _RecordAPI:
    player: 'Player'
    summary: 'SummariesSoloSuccessModel'
    entries: list['ApiRecord']
    record_requests: list[URL]


@pytest.fixture
def record_api(monkeypatch: pytest.MonkeyPatch) -> _RecordAPI:
    from nonebot_plugin_tetris_stats.games.tetrio.api import player as player_module  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import Player  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.user import User  # noqa: PLC0415

    api = _RecordAPI(Player(user_id='user-id', trust=True), _summary(None), [], [])

    async def get(url: URL) -> bytes:
        if '/summaries/' in url.path:
            return api.summary.model_dump_json(by_alias=True).encode()
        api.record_requests.append(url)
        entries = api.entries
        if (after := url.query.get('after')) is not None:
            pri, sec, ter = map(float, after.split(':'))
            entries = [entry for entry in entries if (entry.p.pri, entry.p.sec, entry.p.ter) < (pri, sec, ter)]
        return _records(entries[: int(url.query.get('limit', '25'))]).model_dump_json(by_alias=True).encode()

    async def add(_: 'TETRIOHistoricalData') -> None:
        return None

    async def user(_: Player) -> User:
        return User(ID='user-id', name='tester')

    async def country(_: Player) -> str:
        return 'JP'

    async def avatar_revision(_: Player) -> None:
        return None

    monkeypatch.setattr(player_module.Cache, 'get', get)
    monkeypatch.setattr(player_module, 'anti_duplicate_add', add)
    monkeypatch.setattr(Player, 'user', property(user))
    monkeypatch.setattr(Player, 'country', property(country))
    monkeypatch.setattr(Player, 'avatar_revision', property(avatar_revision))
    return api


@pytest.mark.parametrize('mode', ['--40l', '--blitz'])
@pytest.mark.parametrize('record_type', ['top', 'recent', 'progression', 'invalid'])
def test_record_command_parses_stateless_selector_and_keeps_default(mode: str, record_type: str) -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordType  # noqa: PLC0415

    default = command.parse(f'tstats TETR.IO record tester {mode}')
    selected = command.parse(f'tstats TETR.IO record tester {mode} --type {record_type} --index {SELECTED_INDEX}')

    assert default.matched  # noqa: S101
    assert 'record_type' not in default.all_matched_args  # noqa: S101
    assert 'index' not in default.all_matched_args  # noqa: S101
    if record_type == 'invalid':
        assert not selected.matched  # noqa: S101
        return
    assert selected.matched  # noqa: S101
    assert selected.all_matched_args['record_type'] is RecordType(record_type)  # noqa: S101
    assert selected.all_matched_args['index'] == SELECTED_INDEX  # noqa: S101


@pytest.mark.asyncio
async def test_record_default_still_uses_summary_pb(monkeypatch: pytest.MonkeyPatch, record_api: _RecordAPI) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.record import blitz, sprint  # noqa: PLC0415

    captured: list[_RenderedRecord] = []

    async def capture(data: _RenderedRecord) -> bytes:
        captured.append(data)
        return b'image'

    monkeypatch.setattr(sprint, 'render_image', capture)
    monkeypatch.setattr(blitz, 'render_image', capture)

    record_api.summary = _summary(_summary_record(_record('40l', 'sprint-summary', flags=RecordFlags(pb=True))))
    assert await sprint.make_sprint_image(record_api.player) == b'image'  # noqa: S101
    record_api.summary = _summary(_summary_record(_record('blitz', 'blitz-summary', flags=RecordFlags(pb=True))))
    assert await blitz.make_blitz_image(record_api.player) == b'image'  # noqa: S101

    assert record_api.record_requests == []  # noqa: S101
    assert [  # noqa: S101
        (item.replay_id, item.personal_best, item.global_rank, item.country_rank, item.query.type, item.query.index)
        for item in captured
    ] == [
        ('sprint-summary', 'current', 9, 9, 'top', 1),
        ('blitz-summary', 'current', 9, 9, 'top', 1),
    ]
    for item in captured:
        payload = loads(item.json(by_alias=True))
        assert payload['user']['country'] == 'JP'  # noqa: S101
        assert payload['query'] == {'type': 'top', 'index': 1}  # noqa: S101
        assert not {'type', 'rank', 'personal_rank'} & payload.keys()  # noqa: S101


@pytest.mark.asyncio
async def test_sprint_top_entries_map_all_v2_record_types(
    monkeypatch: pytest.MonkeyPatch, record_api: _RecordAPI
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import sprint  # noqa: PLC0415

    record_api.entries = [
        _record('40l', 'best', flags=RecordFlags(pb=True)),
        _record('40l', 'personal-best', flags=RecordFlags(oncepb=True)),
        _record('40l', 'recent'),
        _record('40l', 'disputed', flags=RecordFlags(pb=True, disputed=True)),
    ]
    player = record_api.player
    captured: list[_RenderedRecord] = []

    async def capture(data: _RenderedRecord) -> bytes:
        captured.append(data)
        return b'image'

    monkeypatch.setattr(sprint, 'render_image', capture)
    for index in range(1, len(record_api.entries) + 1):
        await sprint.make_sprint_image(player, RecordType.Top, index)

    assert [  # noqa: S101
        (item.replay_id, item.personal_best, item.disputed, item.global_rank, item.query.index) for item in captured
    ] == [
        ('best', 'current', False, None, 1),
        ('personal-best', 'former', False, None, 2),
        ('recent', None, False, None, 3),
        ('disputed', 'current', True, None, 4),
    ]
    assert all(item.country_rank is None and item.query.type == 'top' for item in captured)  # noqa: S101


@pytest.mark.asyncio
async def test_blitz_recent_selection_does_not_treat_recency_as_personal_rank(
    monkeypatch: pytest.MonkeyPatch, record_api: _RecordAPI
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import blitz  # noqa: PLC0415

    record_api.entries = [_record('blitz', 'recent'), _record('blitz', 'current-pb', flags=RecordFlags(pb=True))]
    player = record_api.player
    captured: list[_RenderedRecord] = []

    async def capture(data: _RenderedRecord) -> bytes:
        captured.append(data)
        return b'image'

    monkeypatch.setattr(blitz, 'render_image', capture)
    await blitz.make_blitz_image(player, RecordType.Recent, 1)
    await blitz.make_blitz_image(player, RecordType.Recent, 2)

    assert [url.path for url in record_api.record_requests] == ['/api/users/user-id/records/blitz/recent']  # noqa: S101
    assert [(item.replay_id, item.personal_best, item.query.type, item.query.index) for item in captured] == [  # noqa: S101
        ('recent', None, 'recent', 1),
        ('current-pb', 'current', 'recent', 2),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['40l', 'blitz'])
@pytest.mark.parametrize('summary_kind', ['matching', 'different', 'missing'])
async def test_summary_rank_belongs_only_to_exact_record(
    monkeypatch: pytest.MonkeyPatch,
    mode: Literal['40l', 'blitz'],
    summary_kind: str,
    record_api: _RecordAPI,
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import blitz, sprint  # noqa: PLC0415

    selected = _record(mode, 'selected', flags=RecordFlags(pb=True, oncepb=True, disputed=True))
    summary = (
        None
        if summary_kind == 'missing'
        else _summary_record(selected if summary_kind == 'matching' else _record(mode, 'other'))
    )
    record_api.entries = [selected]
    record_api.summary = _summary(summary, rank=8, rank_local=3)
    player = record_api.player
    captured: list[_RenderedRecord] = []

    async def capture(data: _RenderedRecord) -> bytes:
        captured.append(data)
        return b'image'

    module = sprint if mode == '40l' else blitz
    monkeypatch.setattr(module, 'render_image', capture)
    if mode == '40l':
        await sprint.make_sprint_image(player, RecordType.Progression, 1)
    else:
        await blitz.make_blitz_image(player, RecordType.Progression, 1)

    payload = loads(captured[0].json(by_alias=True))
    assert payload['query'] == {'type': 'progression', 'index': 1}  # noqa: S101
    assert payload['personal_best'] == 'current'  # noqa: S101
    assert payload['disputed'] is True  # noqa: S101
    assert payload['global_rank'] == (8 if summary_kind == 'matching' else None)  # noqa: S101
    assert payload['country_rank'] == (3 if summary_kind == 'matching' else None)  # noqa: S101
    assert payload['user']['country'] == 'JP'  # noqa: S101
    assert not {'type', 'rank', 'personal_rank'} & payload.keys()  # noqa: S101


@pytest.mark.asyncio
@pytest.mark.parametrize('rank', [-1, 0])
@pytest.mark.parametrize('mode', ['40l', 'blitz'])
async def test_summary_nonpositive_ranks_become_null(
    rank: int, mode: Literal['40l', 'blitz'], record_api: _RecordAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.record import blitz, sprint  # noqa: PLC0415

    record_api.summary = _summary(_summary_record(_record(mode, 'unranked')), rank=rank, rank_local=rank)
    captured: list[_RenderedRecord] = []

    async def capture(data: _RenderedRecord) -> bytes:
        captured.append(data)
        return b'image'

    monkeypatch.setattr(sprint if mode == '40l' else blitz, 'render_image', capture)
    render = sprint.make_sprint_image if mode == '40l' else blitz.make_blitz_image
    await render(record_api.player)
    assert captured[0].global_rank is None  # noqa: S101
    assert captured[0].country_rank is None  # noqa: S101
    assert captured[0].query.type == 'top' and captured[0].query.index == 1  # noqa: S101


@pytest.mark.asyncio
@pytest.mark.parametrize(('oncepb', 'expected'), [(True, 'former'), (False, None)])
async def test_summary_flags_are_not_inferred_from_default_query(
    monkeypatch: pytest.MonkeyPatch, record_api: _RecordAPI, *, oncepb: bool, expected: str | None
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.record import sprint  # noqa: PLC0415

    record_api.summary = _summary(_summary_record(_record('40l', 'former', flags=RecordFlags(oncepb=oncepb))))
    player = record_api.player
    captured: list[_RenderedRecord] = []

    async def capture(data: _RenderedRecord) -> bytes:
        captured.append(data)
        return b'image'

    monkeypatch.setattr(sprint, 'render_image', capture)
    await sprint.make_sprint_image(player)
    assert captured[0].personal_best == expected  # noqa: S101
    assert captured[0].query.type == 'top' and captured[0].query.index == 1  # noqa: S101


@pytest.mark.asyncio
async def test_record_country_can_be_unknown_or_masked(monkeypatch: pytest.MonkeyPatch, record_api: _RecordAPI) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import Player  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.mask import apply_mask  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import sprint  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.v2.tetrio.record.sprint import Record  # noqa: PLC0415

    record_api.summary = _summary(_summary_record(_record('40l', 'unknown-country')))
    player = record_api.player
    captured: list[Record] = []

    async def capture(data: Record) -> bytes:
        captured.append(data)
        return b'image'

    async def unknown_country(_: Player) -> None:
        return None

    monkeypatch.setattr(sprint, 'render_image', capture)
    await sprint.make_sprint_image(player)
    apply_mask(captured[0].user, {'country'})
    assert loads(captured[0].json(by_alias=True))['user']['country'] is None  # noqa: S101

    monkeypatch.setattr(Player, 'country', property(unknown_country))
    await sprint.make_sprint_image(player)
    assert loads(captured[1].json(by_alias=True))['user']['country'] is None  # noqa: S101


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
    record_api: _RecordAPI,
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordType  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import sprint  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.exception import RecordNotFoundError  # noqa: PLC0415

    record_api.entries = [
        _record('40l', f'record-{position}', order=position) for position in range(1, entry_count + 1)
    ]

    async def unexpected_render(_: _RenderedRecord) -> bytes:
        pytest.fail('out-of-range records must not be rendered')

    async def no_mask(_: str) -> frozenset[str]:
        return frozenset()

    monkeypatch.setattr(sprint, 'get_mask', no_mask)
    monkeypatch.setattr(sprint, 'render_image', unexpected_render)
    with pytest.raises(RecordNotFoundError):
        await sprint.make_sprint_image(record_api.player, RecordType.Top, index)


@pytest.mark.asyncio
async def test_record_index_26_expands_the_first_page(record_api: _RecordAPI) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordModeType, RecordType  # noqa: PLC0415

    record_api.entries = [
        _record('40l', f'record-{index}', order=index) for index in range(1, INDEX_AFTER_DEFAULT_PAGE + 1)
    ]

    record = await record_api.player.get_record(RecordModeType.Sprint, RecordType.Top, index=INDEX_AFTER_DEFAULT_PAGE)

    assert record is not None  # noqa: S101
    assert record.replayid == 'record-26'  # noqa: S101
    assert len(record_api.record_requests) == 1  # noqa: S101
    assert dict(record_api.record_requests[0].query) == {'limit': '26'}  # noqa: S101


@pytest.mark.asyncio
async def test_record_index_paginates_past_100_entries(record_api: _RecordAPI) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordModeType, RecordType  # noqa: PLC0415

    record_api.entries = [_record('40l', f'record-{index}', order=index) for index in range(1, CROSS_PAGE_INDEX + 1)]

    record = await record_api.player.get_record(RecordModeType.Sprint, RecordType.Top, index=CROSS_PAGE_INDEX)

    assert record is not None  # noqa: S101
    assert record.replayid == 'record-125'  # noqa: S101
    assert len(record_api.record_requests) == EXPECTED_PAGE_REQUESTS  # noqa: S101
    assert dict(record_api.record_requests[0].query) == {'limit': '100'}  # noqa: S101
    assert dict(record_api.record_requests[1].query) == {'after': '-100.0:0.0:0.0'}  # noqa: S101


@pytest.mark.asyncio
async def test_record_index_returns_none_only_after_the_last_page_is_exhausted(record_api: _RecordAPI) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.api.player import RecordModeType, RecordType  # noqa: PLC0415

    record_api.entries = [_record('40l', f'record-{index}', order=index) for index in range(1, API_PAGE_LIMIT + 1)]

    record = await record_api.player.get_record(RecordModeType.Sprint, RecordType.Top, index=OUT_OF_RANGE_INDEX)

    assert record is None  # noqa: S101
    assert len(record_api.record_requests) == EXPECTED_PAGE_REQUESTS  # noqa: S101
    assert dict(record_api.record_requests[1].query) == {'after': '-100.0:0.0:0.0', 'limit': '1'}  # noqa: S101


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
    default_top = await player.get_records(RecordModeType.Sprint, RecordType.Top)
    explicit_default = await player.get_records(RecordModeType.Sprint, RecordType.Top, parameter=Parameter())
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
    before_first_page = await player.get_records(
        RecordModeType.Sprint,
        RecordType.Top,
        parameter=Parameter(before=Prisecter('100:0:0'), limit=100),
    )
    before_second_page = await player.get_records(
        RecordModeType.Sprint,
        RecordType.Top,
        parameter=Parameter(before=Prisecter('200:0:0'), limit=100),
    )

    assert repeated is top_limit_one  # noqa: S101
    assert top_limit_two is not top_limit_one  # noqa: S101
    assert recent is not top_limit_one  # noqa: S101
    assert blitz is not top_limit_one  # noqa: S101
    assert explicit_default is default_top  # noqa: S101
    assert default_top is not top_limit_one  # noqa: S101
    assert repeated_first_page is first_page  # noqa: S101
    assert second_page is not first_page  # noqa: S101
    assert before_second_page is not before_first_page  # noqa: S101
    assert len(requested) == EXPECTED_CACHE_REQUESTS  # noqa: S101
    assert len(set(requested)) == EXPECTED_CACHE_REQUESTS  # noqa: S101
