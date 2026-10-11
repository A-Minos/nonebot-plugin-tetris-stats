"""Tests for StructuredHelpFormatter and HelpData schema."""

import json
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

import pytest
from arclet.alconna import Alconna, Args, CommandMeta, Option, Subcommand, command_manager, output_manager
from tarina.lang import lang  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData


@pytest.fixture
def select_locale() -> Iterator[Callable[[str], object]]:
    previous = lang.current
    yield lang.select
    lang.select(previous)


@pytest.fixture
def alc() -> Iterator[Alconna]:
    from nonebot_plugin_tetris_stats.utils.help import StructuredHelpFormatter  # noqa: PLC0415

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

    with output_manager.capture(alc.name) as cap:
        output_manager.set_action(action, command=alc.name)
        alc.parse(cmd)
    if captured:
        return captured[-1]
    out = cap.get('output')
    assert out is not None, f'no output captured for {cmd!r}'  # noqa: S101
    return out


@pytest.mark.parametrize(
    ('description', 'visible'),
    [
        ('[hidden] Unlisted shortcut', False),
        ('Unlisted shortcut [hidden]', False),
        ('An Easter egg!', True),
    ],
)
def test_shortcut_visibility_uses_description_marker(alc: Alconna, description: str, *, visible: bool) -> None:
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    alc.shortcut(
        'visibility-probe',
        command='tstats io query',
        arguments=['testuser'],
        fuzzy=False,
        humanized=description,
    )
    try:
        data = HelpData.model_validate_json(_capture(alc, 'tstats io query --help'))
        assert [shortcut.label for shortcut in data.command.shortcuts] == ([description] if visible else [])  # noqa: S101
        assert alc.parse('visibility-probe').matched  # noqa: S101
    finally:
        command_manager.delete_shortcut(alc, 'visibility-probe')


@pytest.mark.parametrize('arguments', [[], ['testuser']])
def test_shortcut_excludes_static_positionals_and_option_values(alc: Alconna, arguments: list[str]) -> None:
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    game = next(node for node in alc.options if isinstance(node, Subcommand) and node.name == 'TETR.IO')
    query = next(node for node in game.options if isinstance(node, Subcommand) and node.name == 'query')
    with command_manager.update(alc):
        query.add(Option('--format', Args['format', str], alias=['-f'], help_text='Output format'))
        query.add(Option('--verbose', help_text='Show details'))
    account = '' if arguments else ' testuser'
    alc.shortcut(
        'fixed-query',
        command=f'tstats io query{account} -f compact',
        arguments=arguments,
        humanized='Pre-filled query',
    )
    try:
        data = HelpData.model_validate_json(_capture(alc, 'tstats io query --help'))
        shortcut = data.command.shortcuts[0]
        assert shortcut.label == 'Pre-filled query'  # noqa: S101
        assert shortcut.args == []  # noqa: S101
        assert [option.name for option in shortcut.options] == ['--verbose']  # noqa: S101
        assert shortcut.notes == ['Output format']  # noqa: S101
        assert [arg.name for arg in data.command.args] == ['account']  # noqa: S101
        result = alc.parse('fixed-query --verbose')
        assert result.matched  # noqa: S101
        assert result.all_matched_args['account'] == 'testuser'  # noqa: S101
        assert result.all_matched_args['format'] == 'compact'  # noqa: S101
    finally:
        command_manager.delete_shortcut(alc, 'fixed-query')


@pytest.mark.parametrize(
    ('prefixes', 'name', 'trigger', 'aliases'),
    [
        ([], 'cmd', 'cmd', []),
        (['/', '!'], 'cmd', '/cmd', ['!cmd', '/cmd']),
        (['tetris-stats', 'tstats'], None, 'tstats', ['tstats']),
    ],
)
def test_literal_command_heads(prefixes: list[str], name: str | None, trigger: str, aliases: list[str]) -> None:
    from nonebot_plugin_tetris_stats.utils.help import StructuredHelpFormatter  # noqa: PLC0415

    command = Alconna(prefixes, *([] if name is None else [name]), formatter_type=StructuredHelpFormatter)
    try:
        data = json.loads(_capture(command, f'{trigger} --help'))
        assert data['command']['name'] == (name or prefixes[0])  # noqa: S101
        assert set(data['command']['aliases']) == set(aliases)  # noqa: S101
    finally:
        command_manager.delete(command)


def test_subcommand_metadata_includes_aliases(alc: Alconna) -> None:
    """Subcommand node must expose canonical name + full aliases."""
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    out = _capture(alc, 'tstats TETR.IO --help')
    data = HelpData.model_validate_json(out)
    assert data.command.name == 'TETR.IO'  # noqa: S101
    assert set(data.command.aliases) == {'io', 'TETRIO'}  # noqa: S101
    assert data.command.description == 'TETR.IO related'  # noqa: S101
    assert data.breadcrumb == ['tstats', 'TETR.IO']  # noqa: S101


def test_production_help_follows_current_locale(select_locale: Callable[[str], object]) -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    select_locale('zh-CN')
    zh = HelpData.model_validate_json(command.formatter.format_node(['TETR.IO', 'query']))

    select_locale('en-US')
    en = HelpData.model_validate_json(command.formatter.format_node(['TETR.IO', 'query']))

    assert (zh.lang, en.lang) == ('zh-CN', 'en-US')  # noqa: S101
    assert zh.breadcrumb == en.breadcrumb == ['tetris-stats', 'TETR.IO', 'query']  # noqa: S101
    assert zh.command.description == '查询 TETR.IO 游戏信息'  # noqa: S101
    assert en.command.description == 'Look up TETR.IO player data'  # noqa: S101
    assert zh.command.args[0].description == '@要查询的用户 / 我 / TETR.IO 用户名 / ID'  # noqa: S101
    assert en.command.args[0].description == '@mention, me, TETR.IO username, or ID'  # noqa: S101
    zh_compare = next(option for option in zh.command.options if option.name == '--compare')
    en_compare = next(option for option in en.command.options if option.name == '--compare')
    assert zh_compare.description == '与多久之前的数据对比'  # noqa: S101
    assert en_compare.description == 'Set how far back to compare'  # noqa: S101
    assert zh_compare.args[0].description == '对比时间间隔\uff08如 7d, 2w, 24h\uff09'  # noqa: S101
    assert en_compare.args[0].description == 'How far back to compare (e.g., 7d, 2w, 24h)'  # noqa: S101
    assert any(shortcut.label == 'io查' for shortcut in zh.command.shortcuts)  # noqa: S101
    assert any(shortcut.label == 'ioquery' for shortcut in en.command.shortcuts)  # noqa: S101


@pytest.mark.parametrize('locale', ['zh-CN', 'zh-TW', 'en-US', 'es-ES', 'ja-JP', 'ko-KR'])
def test_production_help_uses_each_supported_locale(locale: str, select_locale: Callable[[str], object]) -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.i18n import Lang  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    select_locale(locale)
    data = HelpData.model_validate_json(_capture(command, 'tstats --help'))

    assert data.lang == locale  # noqa: S101
    assert data.command.description == Lang.command.root.description(locale)  # noqa: S101
    assert data.usage == Lang.command.root.usage(locale)  # noqa: S101
    assert data.examples == Lang.command.root.examples(locale).splitlines()  # noqa: S101
    for example in data.examples:
        assert command.parse(example).matched, example  # noqa: S101

    mask_data = HelpData.model_validate_json(_capture(command, 'tstats TETR.IO mask --help'))
    for action in ('add', 'remove'):
        node = next(child for child in mask_data.command.subcommands if child.name == action)
        resource = getattr(Lang.command.tetrio.mask, action)
        assert node.description == resource.description(locale)  # noqa: S101
        assert {arg.name: arg.description for arg in node.args} == {  # noqa: S101
            'account': resource.args.account.notice(locale),
            'fields': resource.args.fields.notice(locale),
        }
    listing = next(node for node in mask_data.command.subcommands if node.name == 'list')
    assert listing.description == Lang.command.tetrio.mask.list.description(locale)  # noqa: S101

    assert mask_data.lang == locale  # noqa: S101
    assert mask_data.breadcrumb == ['tetris-stats', 'TETR.IO', 'mask']  # noqa: S101
    assert mask_data.command.description == Lang.command.tetrio.mask.description(locale)  # noqa: S101


def test_production_help_metadata_comes_from_lang() -> None:
    """Help text on the production command tree must reference Lang, not inline literals."""
    from arclet.alconna.base import Completion, Help, Shortcut  # noqa: PLC0415
    from tarina.lang.model import LangItem  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415

    literals: list[str] = []

    def visit(node: Option | Subcommand, path: str) -> None:
        # Alconna fills a missing help_text with dest, so a missing description also fails here.
        if not isinstance(node.help_text, LangItem):
            literals.append(f'{path}: help_text={node.help_text!r}')
        literals.extend(
            f'{path} <{arg.name}>: notice={arg.notice!r}'
            for arg in node.args.argument
            if arg.notice is not None and not isinstance(arg.notice, LangItem)
        )
        if isinstance(node, Subcommand):
            for child in node.options:
                if not isinstance(child, (Help, Completion, Shortcut)):
                    visit(child, f'{path} {child.name}')

    visit(command, command.header_display)
    literals.extend(
        f'shortcut: {key!r}'
        for key in command_manager.get_shortcut(command)
        if not isinstance(key, LangItem) and '[hidden]' not in key
    )

    assert not literals, literals  # noqa: S101


def test_every_english_shortcut_is_displayed_and_matches(select_locale: Callable[[str], object]) -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    cases = (
        ('iobind', 'iobind testuser', 'TETRIO.bind'),
        ('ioconfig', 'ioconfig', 'TETRIO.config'),
        ('io屏蔽', 'io屏蔽 testuser name', 'TETRIO.mask.add'),
        ('io解屏蔽', 'io解屏蔽 testuser name', 'TETRIO.mask.remove'),
        ('io屏蔽列表', 'io屏蔽列表', 'TETRIO.mask.list'),
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
    select_locale('en-US')
    help_data = HelpData.model_validate_json(command.formatter.format_node())

    for humanized, trigger, target in cases:
        owner = help_data.command
        for part in target.split('.'):
            owner = next(node for node in owner.subcommands if part == node.name or part in node.aliases)
        assert humanized in {shortcut.label for shortcut in owner.shortcuts}, humanized  # noqa: S101
        result = command.parse(trigger)
        assert result.matched, trigger  # noqa: S101
        assert result.find(target), (trigger, target)  # noqa: S101


def test_production_help_contract_details(select_locale: Callable[[str], object]) -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    select_locale('en-US')
    root = HelpData.model_validate_json(command.formatter.format_node())
    assert root.command.name == 'tetris-stats'  # noqa: S101
    assert set(root.command.aliases) == {'tstats'}  # noqa: S101
    tetrio = next(node for node in root.command.subcommands if node.name == 'TETR.IO')

    assert root.command.shortcuts == tetrio.shortcuts == []  # noqa: S101
    record = next(node for node in tetrio.subcommands if node.name == 'record')
    shortcuts = {shortcut.label: shortcut for shortcut in record.shortcuts}
    assert set(shortcuts) == {'iorecordblitz', 'iorecord40l'}  # noqa: S101
    assert [arg.name for arg in shortcuts['iorecordblitz'].args] == ['who']  # noqa: S101
    assert {option.name for option in shortcuts['iorecordblitz'].options} == {  # noqa: S101
        '--40l',
        '--type',
        '--index',
    }
    assert {option.name for option in shortcuts['iorecord40l'].options} == {  # noqa: S101
        '--blitz',
        '--type',
        '--index',
    }
    blitz = next(option for option in record.options if option.name == '--blitz')
    assert shortcuts['iorecordblitz'].notes == [blitz.description]  # noqa: S101
    rank = next(node for node in tetrio.subcommands if node.name == 'rank')
    assert [shortcut.label for shortcut in rank.shortcuts] == ['iorank']  # noqa: S101
    assert rank.shortcuts[0].notes == [rank.description]  # noqa: S101
    assert all(node.shortcuts == [] for node in rank.subcommands)  # noqa: S101
    mask = next(node for node in tetrio.subcommands if node.name == 'mask')
    assert mask.shortcuts == []  # noqa: S101
    assert {node.name: [shortcut.label for shortcut in node.shortcuts] for node in mask.subcommands} == {  # noqa: S101
        'add': ['io屏蔽'],
        'remove': ['io解屏蔽'],
        'list': ['io屏蔽列表'],
    }
    assert command.parse('iorecordblitz me').find('TETRIO.record.blitz')  # noqa: S101
    assert command.parse('iorecord40l me').find('TETRIO.record.sprint')  # noqa: S101

    mask_add = HelpData.model_validate_json(command.formatter.format_node(['TETR.IO', 'mask', 'add']))
    fields = {arg.name: arg for arg in mask_add.command.args}
    assert (fields['account'].optional, fields['account'].variadic) == (False, False)  # noqa: S101
    assert (fields['fields'].optional, fields['fields'].variadic) == (True, True)  # noqa: S101


def test_args_metadata() -> None:
    from nonebot_plugin_tetris_stats.utils.help import StructuredHelpFormatter  # noqa: PLC0415
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
        assert x.description == 'X notice'  # noqa: S101
        assert x.default == '42'  # noqa: S101
        y = args_by_name['y']
        assert y.description == 'str'  # noqa: S101
        assert y.default is None  # noqa: S101
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


def test_alias_tokens_route_to_canonical_subcommand() -> None:
    """Aliases at any depth select the same help page as canonical names."""
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    data = HelpData.model_validate_json(_capture(command, 'tstats io mask add --help'))
    assert data.breadcrumb == ['tetris-stats', 'TETR.IO', 'mask', 'add']  # noqa: S101
    assert data.command.name == 'add'  # noqa: S101


def test_option_help_shows_owning_subcommand(select_locale: Callable[[str], object]) -> None:
    """`--help` after an option renders the subcommand that owns the option."""
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    select_locale('en-US')
    data = HelpData.model_validate_json(_capture(command, 'tstats TETR.IO record --blitz --help'))
    assert data.breadcrumb == ['tetris-stats', 'TETR.IO', 'record']  # noqa: S101
    assert {shortcut.label for shortcut in data.command.shortcuts} == {'iorecordblitz', 'iorecord40l'}  # noqa: S101


async def test_help_output_becomes_image(alc: Alconna, monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_alconna.uniseg import Image  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.utils import help as help_module  # noqa: PLC0415

    async def render(data: 'HelpData') -> bytes:
        assert data.breadcrumb == ['tstats', 'TETR.IO', 'query']  # noqa: S101
        assert data.command.description == 'query account'  # noqa: S101
        return b'help-image'

    monkeypatch.setattr(help_module, 'render_image', render)
    content = _capture(alc, 'tstats io query --help')
    message = await help_module.HelpImageExtension().output_converter('help', content)

    assert len(message) == 1  # noqa: S101
    assert isinstance(message[0], Image)  # noqa: S101
    assert message[0].raw == b'help-image'  # noqa: S101


async def test_non_help_output_keeps_text_fallback() -> None:
    from nonebot_plugin_tetris_stats.utils.help import HelpImageExtension  # noqa: PLC0415

    message = await HelpImageExtension().output_converter('error', 'invalid command')

    assert not message  # noqa: S101


async def test_help_render_failure_preserves_original_error(alc: Alconna, monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats.utils import help as help_module  # noqa: PLC0415

    error = OSError('renderer unavailable')

    async def render(data: 'HelpData') -> bytes:
        assert data.command.name == 'query'  # noqa: S101
        raise error

    monkeypatch.setattr(help_module, 'render_image', render)
    with pytest.raises(OSError) as exc_info:
        await help_module.HelpImageExtension().output_converter('help', _capture(alc, 'tstats io query --help'))

    assert exc_info.value is error  # noqa: S101


def test_help_json_contains_complete_current_command(alc: Alconna) -> None:
    from nonebot_plugin_tetris_stats.utils.render.schemas.help import HelpData  # noqa: PLC0415

    data = json.loads(_capture(alc, 'tstats --help'))
    command_fields = {'name', 'aliases', 'description', 'args', 'options', 'subcommands', 'shortcuts'}

    assert set(data) == {'lang', 'breadcrumb', 'command', 'usage', 'examples'}  # noqa: S101
    assert set(data['command']) == command_fields  # noqa: S101
    game = data['command']['subcommands'][0]
    assert set(game) == command_fields  # noqa: S101
    assert game['options'] == [  # noqa: S101
        {'name': '--flag', 'aliases': [], 'args': [], 'description': 'a flag'}
    ]
    query = game['subcommands'][0]
    assert set(query) == command_fields  # noqa: S101
    assert query['args'] == [  # noqa: S101
        {'name': 'account', 'description': 'str', 'optional': False, 'variadic': False, 'default': None}
    ]
    schema = HelpData.model_json_schema()
    for model in [schema, *schema['$defs'].values()]:
        assert set(model['required']) == set(model['properties'])  # noqa: S101
