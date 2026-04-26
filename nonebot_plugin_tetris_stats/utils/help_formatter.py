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
from typing_extensions import override

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
    """Returns a HelpData JSON string instead of plain text help.

    Caller MUST back-fill ``root`` after Alconna instantiation::

        command = Alconna(..., formatter_type=StructuredHelpFormatter)
        command.formatter.root = command  # type: ignore[attr-defined]
    """

    root: Alconna | None = None

    @override
    def format(self, trace: Trace) -> str:
        from .render.schemas.help import HelpData, HelpNode, HelpOption  # noqa: PLC0415

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
            cur_aliases = [p for p in self.root.prefixes if p != cur_name]
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
        data = HelpData(lang=get_lang(), command=node, breadcrumb=breadcrumb)
        return HELP_JSON_PREFIX + data.model_dump_json(by_alias=True)
