"""Extension that converts structured help JSON into an image message,
and rewrites alias subcommand tokens before --help so Alconna can route the
help request to the correct subcommand.

WARNING - exclusive semantics: ``SelectedExtensions.output_converter()`` uses a
"first override returns" semantic (see nonebot_plugin_alconna/extension.py:248-259),
NOT a chain. Only ONE output_converter Extension may be attached to a given
matcher. Future error / shortcut / completion output customisation MUST be
merged into this Extension - do NOT stack additional ones.

WARNING - depends on ``on_alconna(auto_send_output=True)``: image messages
flow through the nbp-alc auto-send path (rule.py:353-375). If this option is
ever turned off, help images will silently stop being sent.
"""

from arclet.alconna import Alconna, Subcommand
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import Extension, UniMessage
from nonebot_plugin_alconna.extension import OutputType
from typing_extensions import override

from .help_formatter import HELP_JSON_PREFIX

# Built-in option names that trigger help. Mirrors Alconna's default
# namespace.builtin_option_name['help'] (-h / --help). We rewrite alias
# subcommand tokens only when one of these is present, to avoid touching
# regular command parsing.
_HELP_TOKENS = frozenset({'--help', '-h'})


def _build_alias_index(root: Alconna) -> dict[str, str]:
    """Map every casefolded alias / dest -> canonical Subcommand.name.

    Only top-level subcommands need rewriting; deeper levels parse normally
    once the first alias token is promoted to its canonical name.
    """
    index: dict[str, str] = {}
    for child in root.options:
        if not isinstance(child, Subcommand):
            continue
        canonical = child.name
        for token in {child.name, child.dest, *child.aliases}:
            cf = token.casefold()
            index.setdefault(cf, canonical)
    return index


class HelpImageExtension(Extension):
    @property
    @override
    def priority(self) -> int:
        return 10

    @property
    @override
    def id(self) -> str:
        return 'tetris-stats:help-image'

    @override
    async def receive_wrapper(
        self,
        bot: Bot,
        event: Event,
        command: Alconna,
        receive: UniMessage,
    ) -> UniMessage:
        # Only rewrite when --help / -h is present; otherwise leave parsing alone.
        text = receive.extract_plain_text()
        tokens = text.split()
        if not tokens or not _HELP_TOKENS.intersection(tokens):
            return receive

        alias_index = _build_alias_index(command)
        if not alias_index:
            return receive

        # Find the first token (after the root command name) that is an alias
        # and promote it to the canonical Subcommand.name. Stop at --help/-h.
        rewritten: list[str] | None = None
        for i, tok in enumerate(tokens[1:], start=1):
            if tok in _HELP_TOKENS:
                break
            canonical = alias_index.get(tok.casefold())
            if canonical is None or canonical == tok:
                continue
            rewritten = [*tokens[:i], canonical, *tokens[i + 1 :]]
            break

        if rewritten is None:
            return receive

        return UniMessage(' '.join(rewritten))

    @override
    async def output_converter(self, output_type: OutputType, content: str) -> UniMessage:
        # Non-help types or content that is not our private envelope: return
        # an empty UniMessage so nbp-alc rule.py:372 (`if not msg`) falls back
        # to the original text. This keeps shortcut / completion / error
        # outputs working unchanged.
        if output_type != 'help' or not content.startswith(HELP_JSON_PREFIX):
            return UniMessage()
        # Lazy import avoids circular dependency with games/* during plugin load
        # (render/__init__.py -> host.py -> games.tetrio.api.cache).
        from .render import render_image  # noqa: PLC0415
        from .render.schemas.help import HelpData  # noqa: PLC0415

        try:
            data = HelpData.model_validate_json(content[len(HELP_JSON_PREFIX) :])
            img = await render_image(data)
        except Exception as e:
            # Extension/render-stage exceptions do NOT land in arp.error_info;
            # they bubble out of send(). Wrap in a semantic exception so logs
            # show the high-level cause clearly.
            msg = 'failed to render structured help image'
            raise RuntimeError(msg) from e
        return UniMessage.image(raw=img)
