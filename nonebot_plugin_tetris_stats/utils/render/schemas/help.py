from nonebot.compat import PYDANTIC_V2
from pydantic import BaseModel
from typing_extensions import override

from .base import Base


class HelpArg(BaseModel):
    name: str
    notice: str | None
    type_repr: str | None
    optional: bool
    hidden: bool
    default: str | None


class HelpOption(BaseModel):
    name: str
    aliases: list[str]
    dest: str
    args: list[HelpArg]
    help_text: str | None


class HelpNode(BaseModel):
    name: str
    dest: str
    aliases: list[str]
    help_text: str | None
    args: list[HelpArg]
    options: list[HelpOption]
    subcommands: list['HelpNode']


if PYDANTIC_V2:
    HelpNode.model_rebuild()
else:
    HelpNode.update_forward_refs()


class HelpShortcut(BaseModel):
    """A shortcut binding, resolved to its canonical target path.

    ``key`` is the human-readable trigger (e.g. ``"io查 ...args"``);
    ``target`` is the canonical breadcrumb of the command it expands to,
    e.g. ``["tstats", "TETR.IO", "query"]``.
    """

    key: str
    target: list[str]


class HelpData(Base):
    command: HelpNode
    breadcrumb: list[str]
    usage: str | None = None
    examples: list[str] = []
    shortcuts: list[HelpShortcut] = []

    @property
    @override
    def path(self) -> str:
        return 'help'
