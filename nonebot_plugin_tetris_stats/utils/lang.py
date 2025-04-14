from typing import cast

from ..i18n.model import Lang
from .typedefs import Lang as LangType


def get_lang() -> LangType:
    return cast('LangType', Lang.template.template_language())
