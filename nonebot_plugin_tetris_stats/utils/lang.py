from typing import NamedTuple, cast

from ..i18n import Lang
from .typedefs import Lang as LangType


class UnbindChoices(NamedTuple):
    yes: str
    no: str

    def is_cancelled(self, response: str | None) -> bool:
        return response is None or response == self.no


def get_lang() -> LangType:
    return cast('LangType', Lang.template.template_language())


def get_unbind_choices(locale: str | None = None) -> UnbindChoices:
    return UnbindChoices(
        yes=Lang.bind.confirm_yes(locale),
        no=Lang.bind.confirm_no(locale),
    )
