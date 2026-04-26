"""Extension that converts structured help JSON into an image message.

WARNING - exclusive semantics: ``SelectedExtensions.output_converter()`` uses a
"first override returns" semantic (see nonebot_plugin_alconna/extension.py:248-259),
NOT a chain. Only ONE output_converter Extension may be attached to a given
matcher. Future error / shortcut / completion output customisation MUST be
merged into this Extension - do NOT stack additional ones.

WARNING - depends on ``on_alconna(auto_send_output=True)``: image messages
flow through the nbp-alc auto-send path (rule.py:353-375). If this option is
ever turned off, help images will silently stop being sent.
"""

from nonebot_plugin_alconna import Extension, UniMessage
from nonebot_plugin_alconna.extension import OutputType
from typing_extensions import override

from .help_formatter import HELP_JSON_PREFIX


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
