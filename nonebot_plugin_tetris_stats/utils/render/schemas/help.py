from typing import Literal

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


HelpNode.model_rebuild()


class HelpData(Base):
    schema_version: Literal[1] = 1
    kind: Literal['help'] = 'help'
    command: HelpNode
    breadcrumb: list[str]
    usage: str | None = None
    examples: list[str] = []
    shortcuts: list[str] = []

    @property
    @override
    def path(self) -> str:
        return 'help'
