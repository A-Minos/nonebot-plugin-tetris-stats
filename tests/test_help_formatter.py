"""Tests for StructuredHelpFormatter and HelpData schema."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from arclet.alconna import Alconna, Args, CommandMeta, Option, Subcommand, command_manager, output_manager

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def alc() -> Iterator[Alconna]:
    from nonebot_plugin_tetris_stats.utils.help_formatter import StructuredHelpFormatter  # noqa: PLC0415

    a = Alconna(
        ['tstats'],
        Subcommand(
            'TETR.IO',
            Subcommand('query', Args['account', str], help_text='query account'),
            Option('--flag', help_text='a flag'),
            alias=['io', 'TETRIO'],
            help_text='TETR.IO related',
        ),
        meta=CommandMeta(description='Tetris stats root command'),
        formatter_type=StructuredHelpFormatter,
    )
    yield a
    command_manager.delete(a)


def _capture(alc: Alconna, cmd: str) -> str:
    captured: list[str] = []

    def action(text: str) -> None:
        captured.append(text)

    with output_manager.capture(alc.header_display) as cap:
        output_manager.set_action(action, command=alc.header_display)
        alc.parse(cmd)
    if captured:
        return captured[-1]
    out = cap.get('output')
    assert out is not None, f'no output captured for {cmd!r}'  # noqa: S101
    return out


@pytest.mark.parametrize('locale', ['zh-CN', 'zh-TW', 'en-US', 'es-ES', 'ja-JP', 'ko-KR'])
def test_help_schema_accepts_supported_locales(locale: str) -> None:
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    data = HelpData.model_validate(
        {
            'lang': locale,
            'command': {
                'name': 'tstats',
                'dest': 'tstats',
                'aliases': [],
                'help_text': None,
                'args': [],
                'options': [],
                'subcommands': [],
            },
            'breadcrumb': ['tstats'],
        }
    )

    assert data.lang == locale  # noqa: S101


def test_root_node_metadata(alc: Alconna) -> None:
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    out = _capture(alc, 'tstats --help')
    data = HelpData.model_validate_json(out)
    assert data.command.name == 'tstats'  # noqa: S101
    assert data.command.help_text == 'Tetris stats root command'  # noqa: S101
    sub_names = {s.name for s in data.command.subcommands}
    assert 'TETR.IO' in sub_names  # noqa: S101


def test_subcommand_metadata_includes_aliases(alc: Alconna) -> None:
    """Subcommand node must expose canonical name + full aliases.

    Note: Alconna upstream does not match alias strings as the subcommand
    trigger token (probe confirmed 'tstats io --help' does NOT enter the
    subcommand). We therefore trigger via the canonical name, but the schema
    must still expose all aliases.
    """
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    out = _capture(alc, 'tstats TETR.IO --help')
    data = HelpData.model_validate_json(out)
    assert data.command.name == 'TETR.IO'  # noqa: S101
    assert set(data.command.aliases) == {'io', 'TETRIO'}  # noqa: S101
    assert data.command.help_text == 'TETR.IO related'  # noqa: S101
    assert data.breadcrumb == ['tstats', 'TETR.IO']  # noqa: S101


def test_deep_subcommand(alc: Alconna) -> None:
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    out = _capture(alc, 'tstats TETR.IO query --help')
    data = HelpData.model_validate_json(out)
    assert data.breadcrumb == ['tstats', 'TETR.IO', 'query']  # noqa: S101
    assert data.command.name == 'query'  # noqa: S101
    assert data.command.help_text == 'query account'  # noqa: S101
    assert [a.name for a in data.command.args] == ['account']  # noqa: S101


def test_production_help_is_request_local_and_does_not_mutate_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    from arclet.alconna import Option  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils import lang  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.help_formatter import _resolve_current_subcommand  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    query = _resolve_current_subcommand(command, ['TETR.IO', 'query'])
    assert query is not None  # noqa: S101
    query_node = query[-1]
    compare = next(option for option in query_node.options if isinstance(option, Option) and option.name == '--compare')
    who = query_node.args.argument[0]
    compare_arg = compare.args.argument[0]
    shortcuts_before = tuple(command_manager.get_shortcut(command))
    metadata_before = (query_node.help_text, who.notice, compare.help_text, compare_arg.notice)

    monkeypatch.setattr(lang, 'get_lang', lambda: 'zh-CN')
    zh_root = HelpData.model_validate_json(command.formatter.format_node())
    zh = HelpData.model_validate_json(command.formatter.format_node(['TETR.IO', 'query']))

    monkeypatch.setattr(lang, 'get_lang', lambda: 'en-US')
    en_root = HelpData.model_validate_json(command.formatter.format_node())
    en = HelpData.model_validate_json(command.formatter.format_node(['TETR.IO', 'query']))

    assert zh_root.command.help_text == '俄罗斯方块相关游戏数据查询'  # noqa: S101
    assert en_root.command.help_text == 'Query player data for Tetris-related games'  # noqa: S101
    assert zh.breadcrumb == en.breadcrumb == ['tetris-stats', 'TETR.IO', 'query']  # noqa: S101
    assert zh.command.help_text == '查询 TETR.IO 游戏信息'  # noqa: S101
    assert en.command.help_text == 'Query TETR.IO game information'  # noqa: S101
    assert zh.command.args[0].notice == '@想要查询的人 / 自己 / TETR.IO 用户名 / ID'  # noqa: S101
    assert en.command.args[0].notice == '@person to query / me / TETR.IO username / ID'  # noqa: S101
    zh_compare = next(option for option in zh.command.options if option.name == '--compare')
    en_compare = next(option for option in en.command.options if option.name == '--compare')
    assert zh_compare.help_text == '指定对比时间距离'  # noqa: S101
    assert en_compare.help_text == 'Specify a comparison time span'  # noqa: S101
    assert zh_compare.args[0].notice == '对比时间距离 (如 7d, 2w, 24h)'  # noqa: S101
    assert en_compare.args[0].notice == 'Comparison time span (e.g. 7d, 2w, 24h)'  # noqa: S101
    assert any(shortcut.key.startswith('io查 ') for shortcut in zh.shortcuts)  # noqa: S101
    assert any(shortcut.key.startswith('ioquery ') for shortcut in en.shortcuts)  # noqa: S101
    assert (  # noqa: S101
        query_node.help_text,
        who.notice,
        compare.help_text,
        compare_arg.notice,
    ) == metadata_before
    assert tuple(command_manager.get_shortcut(command)) == shortcuts_before  # noqa: S101


def test_production_help_catalog_is_complete() -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.help_catalog import validate_help_catalog  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    data = HelpData.model_validate_json(command.formatter.format_node())

    validate_help_catalog(data)


def test_help_catalog_rejects_unregistered_production_metadata() -> None:
    from nonebot_plugin_tetris_stats.utils.help_catalog import validate_help_catalog  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData, HelpNode  # noqa: PLC0415

    data = HelpData(
        lang='zh-CN',
        command=HelpNode(
            name='missing',
            dest='missing',
            aliases=[],
            help_text='未登记的说明',
            args=[],
            options=[],
            subcommands=[],
        ),
        breadcrumb=['tetris-stats', 'missing'],
    )

    with pytest.raises(ValueError, match=r'description.*tetris-stats.*missing'):
        validate_help_catalog(data)


def test_every_english_shortcut_is_displayed_and_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils import lang  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    cases = (
        ('iobind', 'iobind testuser', 'TETRIO.bind'),
        ('ioconfig', 'ioconfig', 'TETRIO.config'),
        ('ioquery', 'ioquery me', 'TETRIO.query'),
        ('iorank', 'iorank', 'TETRIO.rank'),
        ('iorecordblitz', 'iorecordblitz me', 'TETRIO.record'),
        ('iorecord40l', 'iorecord40l me', 'TETRIO.record'),
        ('iounbind', 'iounbind', 'TETRIO.unbind'),
        ('ioverify', 'ioverify', 'TETRIO.verify'),
        ('topbind', 'topbind testuser', 'TOP.bind'),
        ('topunbind', 'topunbind', 'TOP.unbind'),
        ('topquery', 'topquery me', 'TOP.query'),
        ('topconfig', 'topconfig', 'TOP.config'),
        ('tosbind', 'tosbind testuser', 'TOS.bind'),
        ('tosunbind', 'tosunbind', 'TOS.unbind'),
        ('tosquery', 'tosquery me', 'TOS.query'),
        ('tosconfig', 'tosconfig', 'TOS.config'),
    )
    monkeypatch.setattr(lang, 'get_lang', lambda: 'en-US')
    help_data = HelpData.model_validate_json(command.formatter.format_node())
    displayed = {shortcut.key for shortcut in help_data.shortcuts}

    for humanized, trigger, target in cases:
        assert any(key == humanized or key.startswith(f'{humanized} ') for key in displayed), humanized  # noqa: S101
        result = command.parse(trigger)
        assert result.matched, trigger  # noqa: S101
        assert result.find(target), (trigger, target)  # noqa: S101


def test_future_option_catalog_entries_apply_when_the_fields_exist() -> None:
    from nonebot_plugin_tetris_stats.utils.help_catalog import localize_help  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import (  # noqa: PLC0415
        HelpArg,
        HelpData,
        HelpNode,
        HelpOption,
    )

    def arg(name: str) -> HelpArg:
        return HelpArg(name=name, notice=None, type_repr='str', optional=False, hidden=False, default=None)

    def data(node: str, options: list[HelpOption]) -> HelpData:
        return HelpData(
            lang='zh-CN',
            command=HelpNode(
                name=node,
                dest=node,
                aliases=[],
                help_text=None,
                args=[],
                options=options,
                subcommands=[],
            ),
            breadcrumb=['tetris-stats', 'TETR.IO', node],
        )

    localized_list = localize_help(
        data(
            'list',
            [HelpOption(name='--sort', aliases=[], dest='sort', args=[arg('sort')], help_text=None)],
        ),
        'en-US',
    )
    sort = localized_list.command.options[0]
    assert sort.help_text == 'Ranking metric'  # noqa: S101
    assert sort.args[0].notice == 'Ranking metric (league, pps, apm, adpm, apl, or adpl)'  # noqa: S101

    localized_record = localize_help(
        data(
            'record',
            [
                HelpOption(name='--type', aliases=[], dest='type', args=[arg('record_type')], help_text=None),
                HelpOption(name='--index', aliases=[], dest='index', args=[arg('index')], help_text=None),
            ],
        ),
        'zh-CN',
    )
    record_type, index = localized_record.command.options
    assert record_type.help_text == '记录类型'  # noqa: S101
    assert record_type.args[0].notice == '记录类型 (top、recent、progression)'  # noqa: S101
    assert index.help_text == '记录序号'  # noqa: S101
    assert index.args[0].notice == '记录序号'  # noqa: S101


def test_args_metadata() -> None:
    from nonebot_plugin_tetris_stats.utils.help_formatter import StructuredHelpFormatter  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    a = Alconna(
        ['t'],
        Subcommand(
            'sub',
            Args['x;?#X notice', int, 42]['y;/', str],
            help_text='sub help',
        ),
        formatter_type=StructuredHelpFormatter,
    )
    try:
        out = _capture(a, 't sub --help')
        data = HelpData.model_validate_json(out)
        args_by_name = {arg.name: arg for arg in data.command.args}
        x = args_by_name['x']
        assert x.optional is True  # noqa: S101
        assert x.notice == 'X notice'  # noqa: S101
        assert x.default == '42'  # noqa: S101
        y = args_by_name['y']
        assert y.hidden is True  # noqa: S101
    finally:
        command_manager.delete(a)


def test_builtins_filtered(alc: Alconna) -> None:
    """Help / Completion / Shortcut nodes must not appear in options."""
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    out = _capture(alc, 'tstats --help')
    data = HelpData.model_validate_json(out)
    opt_names = {o.name for o in data.command.options}
    assert '--help' not in opt_names  # noqa: S101
    assert '--shortcut' not in opt_names  # noqa: S101
    assert '--comp' not in opt_names  # noqa: S101


def test_resolve_unknown_path_returns_none() -> None:
    """Mismatched command tree / breadcrumb is a real bug; must fail-fast."""
    from nonebot_plugin_tetris_stats.utils.help_formatter import (  # noqa: PLC0415
        StructuredHelpFormatter,
        _resolve_current_subcommand,
    )

    a = Alconna(['x'], Subcommand('a'), formatter_type=StructuredHelpFormatter)
    try:
        assert _resolve_current_subcommand(a, ['nonexist']) is None  # noqa: S101
    finally:
        command_manager.delete(a)


def test_alias_index_built_from_subcommands(alc: Alconna) -> None:
    """The Extension's alias index must map every alias / dest -> canonical name."""
    from nonebot_plugin_tetris_stats.utils.help_extension import _build_alias_index  # noqa: PLC0415

    index = _build_alias_index(alc)
    assert index['tetr.io'] == 'TETR.IO'  # canonical (casefolded)  # noqa: S101
    assert index['io'] == 'TETR.IO'  # alias  # noqa: S101
    assert index['tetrio'] == 'TETR.IO'  # alias + dest (casefolded)  # noqa: S101
