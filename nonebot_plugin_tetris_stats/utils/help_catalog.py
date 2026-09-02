"""Request-local command help translations.

The Alconna command tree is process-global and intentionally keeps its static
Chinese metadata.  This module overlays a newly-built ``HelpData`` value for
one explicit locale; it never reads or mutates the shared command tree.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal

from tarina.lang.model import LangItem

from ..i18n import Lang

if TYPE_CHECKING:
    from .render.schemas.help import HelpArg, HelpData, HelpNode, HelpOption, HelpShortcut

Breadcrumb = tuple[str, ...]
FieldKind = Literal['description', 'arg', 'option', 'option_arg']
Locale = Literal['zh-CN', 'zh-TW', 'en-US', 'es-ES', 'ja-JP', 'ko-KR']


@dataclass(frozen=True)
class _FieldIdentity:
    breadcrumb: Breadcrumb
    kind: FieldKind
    name: str = ''
    arg_name: str = ''


@dataclass(frozen=True)
class _ShortcutIdentity:
    target: Breadcrumb
    humanized: str


_ROOT = 'tetris-stats'
_TETRIO = (_ROOT, 'TETR.IO')
_TOP = (_ROOT, 'TOP')
_TOS = (_ROOT, 'TOS')

# Canonical Alconna breadcrumbs and field identities are the catalog keys.
# Entries for not-yet-present fields are harmless: traversal only visits
# nodes/arguments/options that exist in the HelpData being localized.
_FIELDS: Mapping[_FieldIdentity, LangItem] = MappingProxyType(
    {
        _FieldIdentity((_ROOT,), 'description'): Lang.command.root.description,
        _FieldIdentity(_TETRIO, 'description'): Lang.command.tetrio.description,
        _FieldIdentity((*_TETRIO, 'bind'), 'description'): Lang.command.tetrio.bind.description,
        _FieldIdentity((*_TETRIO, 'bind'), 'arg', 'account'): Lang.command.tetrio.bind.args.account.notice,
        _FieldIdentity((*_TETRIO, 'config'), 'description'): Lang.command.tetrio.config.description,
        _FieldIdentity(
            (*_TETRIO, 'config'), 'option', '--default-template'
        ): Lang.command.tetrio.config.options.default_template.help,
        _FieldIdentity(
            (*_TETRIO, 'config'), 'option_arg', '--default-template', 'template'
        ): Lang.command.tetrio.config.options.default_template.args.template.notice,
        _FieldIdentity(
            (*_TETRIO, 'config'), 'option', '--default-compare'
        ): Lang.command.tetrio.config.options.default_compare.help,
        _FieldIdentity(
            (*_TETRIO, 'config'), 'option_arg', '--default-compare', 'compare'
        ): Lang.command.tetrio.config.options.default_compare.args.compare.notice,
        _FieldIdentity((*_TETRIO, 'list'), 'description'): Lang.command.tetrio.list.description,
        _FieldIdentity((*_TETRIO, 'list'), 'option', '--max-tr'): Lang.command.tetrio.list.options.max_tr.help,
        _FieldIdentity((*_TETRIO, 'list'), 'option', '--min-tr'): Lang.command.tetrio.list.options.min_tr.help,
        _FieldIdentity((*_TETRIO, 'list'), 'option', '--limit'): Lang.command.tetrio.list.options.limit.help,
        _FieldIdentity((*_TETRIO, 'list'), 'option', '--country'): Lang.command.tetrio.list.options.country.help,
        # Pre-seeded for #452. No matching option means no output change.
        _FieldIdentity((*_TETRIO, 'list'), 'option', '--sort'): Lang.command.tetrio.list.options.sort.help,
        _FieldIdentity(
            (*_TETRIO, 'list'), 'option_arg', '--sort', 'sort'
        ): Lang.command.tetrio.list.options.sort.args.sort.notice,
        _FieldIdentity((*_TETRIO, 'query'), 'description'): Lang.command.tetrio.query.description,
        _FieldIdentity((*_TETRIO, 'query'), 'arg', 'who'): Lang.command.tetrio.query.args.who.notice,
        _FieldIdentity((*_TETRIO, 'query'), 'option', '--template'): Lang.command.tetrio.query.options.template.help,
        _FieldIdentity(
            (*_TETRIO, 'query'), 'option_arg', '--template', 'template'
        ): Lang.command.tetrio.query.options.template.args.template.notice,
        _FieldIdentity((*_TETRIO, 'query'), 'option', '--compare'): Lang.command.tetrio.query.options.compare.help,
        _FieldIdentity(
            (*_TETRIO, 'query'), 'option_arg', '--compare', 'compare'
        ): Lang.command.tetrio.query.options.compare.args.compare.notice,
        _FieldIdentity((*_TETRIO, 'rank'), 'description'): Lang.command.tetrio.rank.description,
        _FieldIdentity((*_TETRIO, 'rank', '--all'), 'description'): Lang.command.tetrio.rank.all.description,
        _FieldIdentity(
            (*_TETRIO, 'rank', '--all'), 'option', '--template'
        ): Lang.command.tetrio.rank.all.options.template.help,
        _FieldIdentity(
            (*_TETRIO, 'rank', '--all'), 'option_arg', '--template', 'template'
        ): Lang.command.tetrio.rank.all.options.template.args.template.notice,
        _FieldIdentity((*_TETRIO, 'rank', '--detail'), 'description'): Lang.command.tetrio.rank.detail.description,
        _FieldIdentity((*_TETRIO, 'rank', '--detail'), 'arg', 'rank'): Lang.command.tetrio.rank.detail.args.rank.notice,
        _FieldIdentity((*_TETRIO, 'record'), 'arg', 'who'): Lang.command.tetrio.record.args.who.notice,
        # Pre-seeded for #345. Missing options/arguments are ignored.
        _FieldIdentity((*_TETRIO, 'record'), 'option', '--type'): Lang.command.tetrio.record.options.type.help,
        _FieldIdentity(
            (*_TETRIO, 'record'), 'option_arg', '--type', 'record_type'
        ): Lang.command.tetrio.record.options.type.args.record_type.notice,
        _FieldIdentity((*_TETRIO, 'record'), 'option', '--index'): Lang.command.tetrio.record.options.index.help,
        _FieldIdentity(
            (*_TETRIO, 'record'), 'option_arg', '--index', 'index'
        ): Lang.command.tetrio.record.options.index.args.index.notice,
        _FieldIdentity((*_TETRIO, 'unbind'), 'description'): Lang.command.tetrio.unbind.description,
        _FieldIdentity((*_TETRIO, 'verify'), 'description'): Lang.command.tetrio.verify.description,
        _FieldIdentity(_TOP, 'description'): Lang.command.top.description,
        _FieldIdentity((*_TOP, 'bind'), 'description'): Lang.command.top.bind.description,
        _FieldIdentity((*_TOP, 'bind'), 'arg', 'account'): Lang.command.top.bind.args.account.notice,
        _FieldIdentity((*_TOP, 'unbind'), 'description'): Lang.command.top.unbind.description,
        _FieldIdentity((*_TOP, 'config'), 'description'): Lang.command.top.config.description,
        _FieldIdentity(
            (*_TOP, 'config'), 'option', '--default-compare'
        ): Lang.command.top.config.options.default_compare.help,
        _FieldIdentity(
            (*_TOP, 'config'), 'option_arg', '--default-compare', 'compare'
        ): Lang.command.top.config.options.default_compare.args.compare.notice,
        _FieldIdentity((*_TOP, 'query'), 'description'): Lang.command.top.query.description,
        _FieldIdentity((*_TOP, 'query'), 'arg', 'who'): Lang.command.top.query.args.who.notice,
        _FieldIdentity((*_TOP, 'query'), 'option', '--compare'): Lang.command.top.query.options.compare.help,
        _FieldIdentity(
            (*_TOP, 'query'), 'option_arg', '--compare', 'compare'
        ): Lang.command.top.query.options.compare.args.compare.notice,
        _FieldIdentity(_TOS, 'description'): Lang.command.tos.description,
        _FieldIdentity((*_TOS, 'bind'), 'description'): Lang.command.tos.bind.description,
        _FieldIdentity((*_TOS, 'bind'), 'arg', 'account'): Lang.command.tos.bind.args.account.notice,
        _FieldIdentity((*_TOS, 'unbind'), 'description'): Lang.command.tos.unbind.description,
        _FieldIdentity((*_TOS, 'config'), 'description'): Lang.command.tos.config.description,
        _FieldIdentity(
            (*_TOS, 'config'), 'option', '--default-compare'
        ): Lang.command.tos.config.options.default_compare.help,
        _FieldIdentity(
            (*_TOS, 'config'), 'option_arg', '--default-compare', 'compare'
        ): Lang.command.tos.config.options.default_compare.args.compare.notice,
        _FieldIdentity((*_TOS, 'query'), 'description'): Lang.command.tos.query.description,
        _FieldIdentity((*_TOS, 'query'), 'arg', 'who'): Lang.command.tos.query.args.who.notice,
        _FieldIdentity((*_TOS, 'query'), 'option', '--compare'): Lang.command.tos.query.options.compare.help,
        _FieldIdentity(
            (*_TOS, 'query'), 'option_arg', '--compare', 'compare'
        ): Lang.command.tos.query.options.compare.args.compare.notice,
    }
)

# These production fields are intentional parser labels rather than user-facing
# prose. They remain untranslated, but every fallback is explicit here.
_FALLBACK_FIELDS = frozenset(
    {
        _FieldIdentity((*_TETRIO, 'record'), 'description'),
        _FieldIdentity((*_TETRIO, 'record'), 'option', '--blitz'),
        _FieldIdentity((*_TETRIO, 'record'), 'option', '--40l'),
    }
)

_SHORTCUTS: Mapping[_ShortcutIdentity, LangItem] = MappingProxyType(
    {
        _ShortcutIdentity((*_TETRIO, 'bind'), 'io绑定'): Lang.command.tetrio.bind.shortcut,
        _ShortcutIdentity((*_TETRIO, 'config'), 'io配置'): Lang.command.tetrio.config.shortcut,
        _ShortcutIdentity((*_TETRIO, 'query'), 'io查'): Lang.command.tetrio.query.shortcut,
        _ShortcutIdentity((*_TETRIO, 'rank'), 'iorank'): Lang.command.tetrio.rank.shortcut,
        _ShortcutIdentity((*_TETRIO, 'record'), 'io记录blitz'): Lang.command.tetrio.record.shortcuts.blitz,
        _ShortcutIdentity((*_TETRIO, 'record'), 'io记录40l'): Lang.command.tetrio.record.shortcuts.sprint,
        _ShortcutIdentity((*_TETRIO, 'unbind'), 'io解绑'): Lang.command.tetrio.unbind.shortcut,
        _ShortcutIdentity((*_TETRIO, 'verify'), 'io验证'): Lang.command.tetrio.verify.shortcut,
        _ShortcutIdentity((*_TOP, 'bind'), 'top绑定'): Lang.command.top.bind.shortcut,
        _ShortcutIdentity((*_TOP, 'unbind'), 'top解绑'): Lang.command.top.unbind.shortcut,
        _ShortcutIdentity((*_TOP, 'query'), 'top查'): Lang.command.top.query.shortcut,
        _ShortcutIdentity((*_TOP, 'config'), 'top配置'): Lang.command.top.config.shortcut,
        _ShortcutIdentity((*_TOS, 'bind'), '茶服绑定'): Lang.command.tos.bind.shortcut,
        _ShortcutIdentity((*_TOS, 'unbind'), '茶服解绑'): Lang.command.tos.unbind.shortcut,
        _ShortcutIdentity((*_TOS, 'query'), '茶服查'): Lang.command.tos.query.shortcut,
        _ShortcutIdentity((*_TOS, 'config'), '茶服配置'): Lang.command.tos.config.shortcut,
    }
)

_LOCALES: Mapping[str, Locale] = MappingProxyType(
    {
        'en': 'en-US',
        'en-us': 'en-US',
        'zh': 'zh-CN',
        'zh-cn': 'zh-CN',
        'zh-hans': 'zh-CN',
    }
)


def _locale(locale: str) -> Locale:
    normalized = locale.strip().replace('_', '-').casefold()
    return _LOCALES.get(normalized, 'en-US')


def _is_production(path: Breadcrumb) -> bool:
    return path[:1] == (_ROOT,)


def _shortcut_item(
    shortcut: 'HelpShortcut', locale: str | None = None
) -> tuple[_ShortcutIdentity, LangItem, str] | None:
    key = shortcut.key
    target = tuple(shortcut.target)
    for identity, item in _SHORTCUTS.items():
        humanized_values = (identity.humanized, item(_locale(locale))) if locale is not None else (identity.humanized,)
        for humanized in humanized_values:
            if identity.target == target and (key == humanized or key.startswith(f'{humanized} ')):
                return identity, item, humanized
    return None


def _missing_field(identity: _FieldIdentity, value: str | None) -> str | None:
    if value is None or not _is_production(identity.breadcrumb) or identity in _FIELDS or identity in _FALLBACK_FIELDS:
        return None
    names = '/'.join(part for part in (identity.name, identity.arg_name) if part)
    suffix = f':{names}' if names else ''
    return f'{identity.kind}:{" / ".join(identity.breadcrumb)}{suffix}'


def _missing_fields(node: 'HelpNode', path: Breadcrumb) -> list[str]:
    identities = [(_FieldIdentity(path, 'description'), node.help_text)]
    identities.extend((_FieldIdentity(path, 'arg', arg.name), arg.notice) for arg in node.args)
    for option in node.options:
        identities.append((_FieldIdentity(path, 'option', option.name), option.help_text))
        identities.extend(
            (_FieldIdentity(path, 'option_arg', option.name, arg.name), arg.notice) for arg in option.args
        )

    missing = [result for identity, value in identities if (result := _missing_field(identity, value)) is not None]
    for child in node.subcommands:
        missing.extend(_missing_fields(child, (*path, child.name)))
    return missing


def _missing_shortcut(shortcut: 'HelpShortcut', locale: str) -> str | None:
    target = tuple(shortcut.target)
    if not _is_production(target) or _shortcut_item(shortcut, locale) is not None:
        return None
    return f'shortcut:{" / ".join(target)}:{shortcut.key}'


def validate_help_catalog(data: 'HelpData') -> None:
    """Reject untranslated production metadata that has no canonical owner."""
    missing = _missing_fields(data.command, tuple(data.breadcrumb))
    missing.extend(
        result for shortcut in data.shortcuts if (result := _missing_shortcut(shortcut, data.lang)) is not None
    )
    if missing:
        message = f'Help catalog is missing identities: {", ".join(missing)}'
        raise ValueError(message)


def _text(identity: _FieldIdentity, fallback: str | None, locale: str) -> str | None:
    item = _FIELDS.get(identity)
    if item is not None:
        return item(locale)
    if fallback is None or not _is_production(identity.breadcrumb) or identity in _FALLBACK_FIELDS:
        return fallback
    message = f'Help catalog is missing identity: {identity!r}'
    raise ValueError(message)


def _arg(arg: 'HelpArg', path: Breadcrumb, locale: str, *, option: str = '') -> 'HelpArg':
    from .render.schemas.help import HelpArg  # noqa: PLC0415

    kind: FieldKind = 'option_arg' if option else 'arg'
    return HelpArg(
        name=arg.name,
        notice=_text(_FieldIdentity(path, kind, option or arg.name, arg.name if option else ''), arg.notice, locale),
        type_repr=arg.type_repr,
        optional=arg.optional,
        hidden=arg.hidden,
        default=arg.default,
    )


def _option(option: 'HelpOption', path: Breadcrumb, locale: str) -> 'HelpOption':
    from .render.schemas.help import HelpOption  # noqa: PLC0415

    return HelpOption(
        name=option.name,
        aliases=list(option.aliases),
        dest=option.dest,
        args=[_arg(arg, path, locale, option=option.name) for arg in option.args],
        help_text=_text(_FieldIdentity(path, 'option', option.name), option.help_text, locale),
    )


def _node(node: 'HelpNode', path: Breadcrumb, locale: str) -> 'HelpNode':
    from .render.schemas.help import HelpNode  # noqa: PLC0415

    return HelpNode(
        name=node.name,
        dest=node.dest,
        aliases=list(node.aliases),
        help_text=_text(_FieldIdentity(path, 'description'), node.help_text, locale),
        args=[_arg(arg, path, locale) for arg in node.args],
        options=[_option(option, path, locale) for option in node.options],
        subcommands=[_node(child, (*path, child.name), locale) for child in node.subcommands],
    )


def _shortcut(shortcut: 'HelpShortcut', locale: str) -> 'HelpShortcut':
    from .render.schemas.help import HelpShortcut  # noqa: PLC0415

    binding = _shortcut_item(shortcut, locale)
    if binding is None:
        if _is_production(tuple(shortcut.target)):
            message = f'Help catalog is missing shortcut identity: {shortcut!r}'
            raise ValueError(message)
        return HelpShortcut(key=shortcut.key, target=list(shortcut.target))
    _, item, humanized = binding
    key = f'{item(locale)}{shortcut.key[len(humanized) :]}'
    return HelpShortcut(key=key, target=list(shortcut.target))


def localize_help(data: 'HelpData', locale: str) -> 'HelpData':
    """Return a translated copy of ``data`` for an explicit request locale."""
    from .render.schemas.help import HelpData  # noqa: PLC0415

    validate_help_catalog(data)

    resolved_locale = _locale(locale)
    path = tuple(data.breadcrumb)
    return HelpData(
        lang=resolved_locale,
        command=_node(data.command, path, resolved_locale),
        breadcrumb=list(data.breadcrumb),
        usage=data.usage,
        examples=list(data.examples),
        shortcuts=[_shortcut(shortcut, resolved_locale) for shortcut in data.shortcuts],
    )


__all__ = ['localize_help', 'validate_help_catalog']
