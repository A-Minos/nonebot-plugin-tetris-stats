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


def test_auto_send_output_remains_true() -> None:
    """Lock the v3.1 design dependency on on_alconna(auto_send_output=True).

    If this is ever turned off, HelpImageExtension.output_converter never
    fires and help images silently stop being sent.
    """
    from nonebot_plugin_tetris_stats.games import alc  # noqa: PLC0415

    rule = next(c for c in alc.rule.checkers if c.call.__class__.__name__ == 'AlconnaRule')
    assert rule.call.auto_send is True  # type: ignore[attr-defined]  # noqa: S101
