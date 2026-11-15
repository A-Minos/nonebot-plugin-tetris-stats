from typing import Self

from arclet.alconna import Alconna, Arg, MultiVar, Option, Subcommand, command_manager
from arclet.alconna.base import Completion, Help, Shortcut
from pydantic import BaseModel
from tarina import Empty
from typing_extensions import override

from .base import Base


class HelpArg(BaseModel):
    name: str
    description: str
    optional: bool
    variadic: bool
    default: str | None

    @classmethod
    def from_arg(cls, arg: Arg) -> Self:
        return cls(
            name=arg.name,
            description=str(arg.notice or arg.value),
            optional=arg.optional or (isinstance(arg.value, MultiVar) and arg.value.flag == '*'),
            variadic=isinstance(arg.value, MultiVar),
            default=None if arg.field.default is Empty else repr(arg.field.default),
        )


class HelpOption(BaseModel):
    name: str
    aliases: list[str]
    description: str | None
    args: list[HelpArg]

    @classmethod
    def from_node(cls, node: Option) -> Self:
        return cls(
            name=node.name,
            aliases=sorted(node.aliases - {node.name}),
            description=str(node.help_text),
            args=[HelpArg.from_arg(arg) for arg in node.args.argument],
        )


class HelpShortcut(BaseModel):
    label: str
    args: list[HelpArg]
    options: list[HelpOption]
    notes: list[str]

    @classmethod
    def from_binding(cls, label: str, node: Subcommand, bindings: list[str]) -> Self:
        args = list(node.args.argument)
        bound_options: list[Option] = []
        while bindings:
            token = bindings.pop(0)
            option = next(
                (option for option in node.options if isinstance(option, Option) and token in option.aliases), None
            )
            if option is not None:
                bound_options.append(option)
                del bindings[: len(option.args.argument)]
            elif args and not isinstance(args[0].value, MultiVar):
                args.pop(0)
        descriptions = [option.help_text for option in bound_options] if bound_options else [node.help_text]
        return cls(
            label=label,
            args=[HelpArg.from_arg(arg) for arg in args],
            options=[
                HelpOption.from_node(option)
                for option in node.options
                if isinstance(option, Option)
                and not isinstance(option, (Help, Completion, Shortcut))
                and option not in bound_options
            ],
            notes=[str(text) for text in descriptions if str(text).strip()],
        )


class HelpCommand(BaseModel):
    name: str
    aliases: list[str]
    description: str | None
    args: list[HelpArg]
    options: list[HelpOption]
    subcommands: list['HelpCommand']
    shortcuts: list[HelpShortcut]

    @classmethod
    def from_node(cls, node: Subcommand) -> Self:
        aliases: set[str] | frozenset[str]
        if isinstance(node, Alconna):
            header = command_manager.require(node).command_header.content
            if not isinstance(header, set):
                message = 'Image help supports only literal text command headers'
                raise TypeError(message)
            aliases = header
        else:
            aliases = node.aliases
        return cls(
            name=node.name,
            aliases=sorted(aliases - {node.name}),
            description=str(node.help_text),
            args=[HelpArg.from_arg(arg) for arg in node.args.argument],
            options=[
                HelpOption.from_node(option)
                for option in node.options
                if isinstance(option, Option) and not isinstance(option, (Help, Completion, Shortcut))
            ],
            subcommands=[cls.from_node(sub) for sub in node.options if isinstance(sub, Subcommand)],
            shortcuts=[],
        )


class HelpData(Base):
    breadcrumb: list[str]
    command: HelpCommand
    usage: str | None
    examples: list[str]

    @property
    @override
    def path(self) -> str:
        return 'help'
