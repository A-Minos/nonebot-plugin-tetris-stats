from collections.abc import Iterable
from itertools import takewhile
from typing import Self

from arclet.alconna import Alconna, Subcommand, TextFormatter, command_manager
from arclet.alconna.typing import InnerShortcutArgs
from nonebot.compat import PYDANTIC_V2, type_validate_json
from nonebot_plugin_alconna import Extension, UniMessage
from nonebot_plugin_alconna.extension import OutputType
from typing_extensions import override

from .lang import get_lang
from .render import render_image
from .render.schemas.help import HelpCommand, HelpData, HelpShortcut


def resolve_target(root: Alconna, args: Iterable[str]) -> tuple[Subcommand, list[str], list[str]]:
    node: Subcommand = root
    path = [root.name]
    remaining: list[str] = []
    for arg in args:
        sub = next(
            (option for option in node.options if isinstance(option, Subcommand) and arg in option.aliases), None
        )
        if sub is not None:
            node = sub
            path.append(sub.name)
            remaining.clear()
        else:
            remaining.append(arg)
    return node, path, remaining


class StructuredHelpFormatter(TextFormatter):
    root: Alconna

    @override
    def add(self, base: Alconna) -> Self:
        self.root = base
        return super().add(base)

    @override
    def format_node(self, parts: list | None = None) -> str:
        _, breadcrumb, _ = resolve_target(self.root, map(str, parts or []))
        command = HelpCommand.from_node(self.root)
        for humanized, short in command_manager.get_shortcut(self.root).items():
            label = str(humanized)
            if '[hidden]' in label:
                continue
            expanded = str(short.command if isinstance(short, InnerShortcutArgs) else short.origin).split()
            fixed = takewhile(lambda token: '{' not in token, expanded[1:])
            node, target, bindings = resolve_target(self.root, fixed)
            if isinstance(short, InnerShortcutArgs):
                bindings.extend(map(str, short.args))
            owner = command
            for name in target[1:]:
                owner = next(child for child in owner.subcommands if child.name == name)
            owner.shortcuts.append(HelpShortcut.from_binding(label, node, bindings))
        for name in breadcrumb[1:]:
            command = next(child for child in command.subcommands if child.name == name)
        meta = self.root.meta
        is_root = len(breadcrumb) == 1
        data = HelpData(
            lang=get_lang(),
            command=command,
            breadcrumb=breadcrumb,
            usage=str(meta.usage) if is_root and meta.usage is not None else None,
            examples=[] if not is_root else [line for line in str(meta.example or '').splitlines() if line.strip()],
        )
        return data.model_dump_json(by_alias=True) if PYDANTIC_V2 else data.json(by_alias=True)


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
        if output_type != 'help':
            return UniMessage()

        return UniMessage.image(raw=await render_image(type_validate_json(HelpData, content)))
