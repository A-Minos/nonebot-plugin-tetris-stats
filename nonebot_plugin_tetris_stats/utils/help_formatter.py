"""Structured help formatter for Alconna.

Overrides Alconna's built-in --help output. ``StructuredHelpFormatter.format()``
returns a prefixed ``HelpData`` JSON string instead of human-readable text;
``HelpImageExtension.output_converter`` later intercepts it and renders an
image message.

fail-fast: this formatter does NOT try/except internally. If node extraction
fails, the exception is wrapped by nonebot-plugin-alconna into
``Arparma(error_info=e)`` and surfaces through the original error path so the
problem is immediately visible. Extension/render-stage exceptions are wrapped
in ``help_extension.py``.
"""

from inspect import Signature
from typing import TYPE_CHECKING

from arclet.alconna import Alconna, Option, Subcommand
from arclet.alconna.args import Arg
from arclet.alconna.base import Completion, Help, Shortcut
from arclet.alconna.formatter import TextFormatter, Trace
from arclet.alconna.manager import command_manager
from arclet.alconna.typing import InnerShortcutArgs
from typing_extensions import Self, override

if TYPE_CHECKING:
    from .render.schemas.help import HelpArg, HelpNode, HelpOption

# Namespaced + versioned envelope. Both the formatter and the extension match
# on this prefix. Future schema bumps go to V2 / V3 for graceful migration.
HELP_JSON_PREFIX = '__NBPTS_HELP_V1__:'

_BUILTINS = (Help, Completion, Shortcut)
_EMPTY = Signature.empty


def _arg_to_help(arg: Arg) -> 'HelpArg':
    from .render.schemas.help import HelpArg  # noqa: PLC0415

    default = arg.field.default
    return HelpArg(
        name=arg.name,
        notice=arg.notice,
        type_repr=getattr(arg.value, '__name__', None) or repr(arg.value),
        optional=arg.optional,
        hidden=arg.hidden,
        default=None if default is _EMPTY else repr(default),
    )


def _opt_to_help(opt: Option) -> 'HelpOption':
    from .render.schemas.help import HelpOption  # noqa: PLC0415

    return HelpOption(
        name=opt.name,
        aliases=[a for a in opt.aliases if a != opt.name],
        dest=opt.dest,
        args=[_arg_to_help(a) for a in opt.args.argument],
        help_text=opt.help_text,
    )


def _sub_to_help(sub: Subcommand) -> 'HelpNode':
    from .render.schemas.help import HelpNode, HelpOption  # noqa: PLC0415

    options: list[HelpOption] = []
    subcommands: list[HelpNode] = []
    for child in sub.options:
        if isinstance(child, _BUILTINS):
            continue
        if isinstance(child, Subcommand):
            subcommands.append(_sub_to_help(child))
        elif isinstance(child, Option):
            options.append(_opt_to_help(child))
    return HelpNode(
        name=sub.name,
        dest=sub.dest,
        aliases=[a for a in sub.aliases if a != sub.name],
        help_text=sub.help_text,
        args=[_arg_to_help(a) for a in sub.args.argument],
        options=options,
        subcommands=subcommands,
    )


def _is_easter_egg(key: str) -> bool:
    """Hidden shortcuts use 'easter egg' marker in their humanized key."""
    return 'easter egg' in key.casefold()


def _extract_command_text(command: object) -> str | None:
    """Extract a plain command path string from InnerShortcutArgs.command.

    The field can be either a raw ``str`` or a list of message segments
    (e.g. ``[Text(text='tstats TETR.IO query', ...)]``) when the shortcut
    flowed through nonebot-plugin-alconna's uniseg layer. We concatenate any
    object that exposes a ``text`` attribute.
    """
    if isinstance(command, str):
        return command
    if isinstance(command, list):
        parts: list[str] = []
        for seg in command:
            text = getattr(seg, 'text', None)
            if isinstance(text, str):
                parts.append(text)
        return ' '.join(parts) if parts else None
    return None


def _is_path_segment(token: str) -> bool:
    """Path segments are command/subcommand names; not flags or placeholders."""
    return not token.startswith(('-', '{'))


def _render_arg_token(name: str, *, optional: bool) -> str:
    return f'[{name}]' if optional else f'<{name}>'


def _render_target_signature(root: Alconna, target: list[str]) -> str:
    """Render the args/options accepted by ``target`` as a usage-style suffix.

    e.g. for shortcut ``io查`` whose target is ``tstats TETR.IO query``, this
    returns ``[--template <template>] [--compare <compare>]``. Hidden args and
    builtin options (--help / --shortcut / --comp) are skipped.
    """
    sub_path = target[1:]
    if not sub_path:
        args_iter = list(root.args.argument)
        children = list(root.options)
    else:
        chain = _resolve_current_subcommand(root, sub_path)
        if chain is None:
            return ''
        sub = chain[-1]
        args_iter = list(sub.args.argument)
        children = list(sub.options)

    tokens: list[str] = []
    tokens.extend(_render_arg_token(a.name, optional=a.optional) for a in args_iter)
    for child in children:
        if isinstance(child, _BUILTINS) or not isinstance(child, Option):
            continue
        inner = [child.name, *(_render_arg_token(a.name, optional=a.optional) for a in child.args.argument)]
        tokens.append(f'[{" ".join(inner)}]')
    return ' '.join(tokens)


def _collect_shortcuts(root: Alconna) -> list[tuple[str, list[str]]]:
    """Return list of (humanized_key, target_path) pairs, filtering easter eggs.

    target_path is the full canonical breadcrumb starting with the root header.
    The humanized key is suffixed with the target command's argument signature
    (rendered in CLI ``<required>`` / ``[optional]`` syntax) so users can see
    what they may / must supply, instead of the opaque ``...args`` placeholder.
    """
    results: list[tuple[str, list[str]]] = []
    for key, short in command_manager.get_shortcut(root).items():
        if _is_easter_egg(key):
            continue
        if not isinstance(short, InnerShortcutArgs):
            # Custom shortcut wrappers: cannot statically resolve target.
            results.append((key, [root.header_display]))
            continue
        cmd_text = _extract_command_text(short.command)
        target = (
            [tok for tok in cmd_text.split() if _is_path_segment(tok)]
            if cmd_text
            else [root.header_display]
        )
        suffix = _render_target_signature(root, target)
        rendered = f'{key} {suffix}' if suffix else key
        results.append((rendered, target))
    return results


def _resolve_current_subcommand(root: Alconna, sub_path: list[str]) -> list[Subcommand] | None:
    """Resolve the canonical subcommand chain along ``sub_path``.

    A segment may look like ``'TETR.IO|io|TETRIO'`` (Alconna joins aliases
    with U+2502 BOX DRAWINGS LIGHT VERTICAL in head['name']) or be a plain
    canonical / alias / dest token. Each segment is split on U+2502 to build
    a candidate set, then casefold-matched against every Subcommand's
    ``name`` / ``aliases`` / ``dest``.

    Returns the chain root->target on success, ``None`` if any segment fails
    to resolve.
    """
    cur_options: list = list(root.options)
    chain: list[Subcommand] = []
    for seg in sub_path:
        candidates_cf = {p.casefold() for p in seg.split('\u2502') if p}
        nxt = next(
            (
                c
                for c in cur_options
                if isinstance(c, Subcommand)
                and (
                    c.name.casefold() in candidates_cf
                    or c.dest.casefold() in candidates_cf
                    or any(a.casefold() in candidates_cf for a in c.aliases)
                )
            ),
            None,
        )
        if nxt is None:
            return None
        chain.append(nxt)
        cur_options = list(nxt.options)
    return chain


class StructuredHelpFormatter(TextFormatter):
    """Returns a HelpData JSON string instead of plain text help."""

    root: Alconna | None = None

    @override
    def add(self, base: Alconna) -> Self:
        self.root = base
        return super().add(base)

    @override
    def format(self, trace: Trace) -> str:
        from .render.schemas.help import HelpData, HelpNode, HelpOption, HelpShortcut  # noqa: PLC0415

        head = trace.head
        # head['name'] looks like 'tstats TETR.IO|io|TETRIO query' where each
        # whitespace-separated segment may contain aliases joined by U+2502.
        # The canonical name is not guaranteed to be the first alias; we
        # therefore split into raw segments and resolve canonical Subcommand
        # objects below.
        raw_segments: list[str] = head['name'].split()
        sub_path = raw_segments[1:]

        options: list[HelpOption] = []
        subcommands: list[HelpNode] = []
        for child in trace.body:
            if isinstance(child, _BUILTINS):
                continue
            if isinstance(child, Subcommand):
                subcommands.append(_sub_to_help(child))
            elif isinstance(child, Option):
                options.append(_opt_to_help(child))

        if self.root is None:
            msg = 'StructuredHelpFormatter.root is not injected; back-fill command.formatter.root after Alconna(...)'
            raise RuntimeError(msg)

        if not sub_path:
            cur_name = self.root.header_display
            cur_dest = self.root.path
            cur_aliases = [str(p) for p in self.root.prefixes if p != cur_name]
            breadcrumb = [cur_name]
        else:
            chain = _resolve_current_subcommand(self.root, sub_path)
            if chain is None:
                msg = f'cannot resolve subcommand for path {sub_path!r}'
                raise RuntimeError(msg)
            sub = chain[-1]
            cur_name = sub.name
            cur_dest = sub.dest
            cur_aliases = [a for a in sub.aliases if a != sub.name]
            breadcrumb = [self.root.header_display, *(s.name for s in chain)]

        # Lazy import avoids circular dependency with games/* (render/__init__.py
        # -> host.py -> games.tetrio.api.cache -> back into games/__init__.py).
        from .lang import get_lang  # noqa: PLC0415

        node = HelpNode(
            name=cur_name,
            dest=cur_dest,
            aliases=cur_aliases,
            help_text=head.get('description'),
            args=[_arg_to_help(a) for a in trace.args],
            options=options,
            subcommands=subcommands,
        )
        # usage / examples / shortcuts only exist on the root Alconna's CommandMeta;
        # Subcommand has no `meta` attribute. Show them only on the root help page.
        all_shortcuts = _collect_shortcuts(self.root)
        if not sub_path:
            usage = self.root.meta.usage
            example_raw = self.root.meta.example
            examples = [line for line in (example_raw or '').splitlines() if line.strip()]
            shortcuts = [HelpShortcut(key=k, target=t) for k, t in all_shortcuts]
        else:
            usage = None
            examples = []
            shortcuts = [HelpShortcut(key=k, target=t) for k, t in all_shortcuts if t[1:len(breadcrumb)] == breadcrumb[1:]]
        data = HelpData(
            lang=get_lang(),
            command=node,
            breadcrumb=breadcrumb,
            usage=usage,
            examples=examples,
            shortcuts=shortcuts,
        )
        return HELP_JSON_PREFIX + data.model_dump_json(by_alias=True)
