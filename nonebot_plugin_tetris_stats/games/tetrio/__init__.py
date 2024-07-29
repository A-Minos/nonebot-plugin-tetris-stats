from arclet.alconna import Arg, ArgFlag, Args, Option, Subcommand
from nonebot_plugin_alconna import At

from ...utils.exception import MessageFormatError
from ...utils.typing import Me

# from .. import add_block_handlers, alc, command
from .. import alc, command
from .api import Player

# from .api.typing import ValidRank
from .constant import USER_ID, USER_NAME
from .typing import Template


def get_player(user_id_or_name: str) -> Player | MessageFormatError:
    if USER_ID.match(user_id_or_name):
        return Player(user_id=user_id_or_name, trust=True)
    if USER_NAME.match(user_id_or_name):
        return Player(user_name=user_id_or_name, trust=True)
    return MessageFormatError('用户名/ID不合法')


command.add(
    Subcommand(
        'TETR.IO',
        Subcommand(
            'bind',
            Args(
                Arg(
                    'account',
                    get_player,
                    notice='TETR.IO 用户名 / ID',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            help_text='绑定 TETR.IO 账号',
        ),
        # Subcommand(
        #     'query',
        #     Args(
        #         Arg(
        #             'target',
        #             At | Me,
        #             notice='@想要查询的人 / 自己',
        #             flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
        #         ),
        #         Arg(
        #             'account',
        #             get_player,
        #             notice='TETR.IO 用户名 / ID',
        #             flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
        #         ),
        #     ),
        #     Option(
        #         '--template',
        #         Arg('template', Template),
        #         alias=['-T'],
        #         help_text='要使用的查询模板',
        #     ),
        #     help_text='查询 TETR.IO 游戏信息',
        # ),
        Subcommand(
            'record',
            Option(
                '--40l',
                dest='sprint',
            ),
            Option(
                '--blitz',
                dest='blitz',
            ),
            Args(
                Arg(
                    'target',
                    At | Me,
                    notice='@想要查询的人 / 自己',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
                Arg(
                    'account',
                    get_player,
                    notice='TETR.IO 用户名 / ID',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
            ),
        ),
        # Subcommand(
        #     'list',
        #     Option('--max-tr', Arg('max_tr', float), help_text='TR的上限'),
        #     Option('--min-tr', Arg('min_tr', float), help_text='TR的下限'),
        #     Option('--limit', Arg('limit', int), help_text='查询数量'),
        #     Option('--country', Arg('country', str), help_text='国家代码'),
        #     help_text='查询 TETR.IO 段位排行榜',
        # ),
        # Subcommand(
        #     'rank',
        #     Subcommand(
        #         '--all',
        #         Option(
        #             '--template',
        #             Arg('template', Template),
        #             alias=['-T'],
        #             help_text='要使用的查询模板',
        #         ),
        #         dest='all',
        #     ),
        #     Option(
        #         '--detail',
        #         Arg('rank', ValidRank),
        #         alias=['-D'],
        #     ),
        #     help_text='查询 TETR.IO 段位信息',
        # ),
        Subcommand(
            'config',
            Option(
                '--default-template',
                Arg('template', Template),
                alias=['-DT', 'DefaultTemplate'],
            ),
        ),
        alias=['TETRIO', 'tetr.io', 'tetrio', 'io'],
        dest='TETRIO',
        help_text='TETR.IO 游戏相关指令',
    )
)


# def rank_wrapper(slot: int | str, content: str | None):
#     if slot == 'rank' and not content:
#         return '--all'
#     if content is not None:
#         return f'--detail {content.lower()}'
#     return content


alc.shortcut(
    '(?i:io)(?i:绑定|绑|bind)',
    command='tstats TETR.IO bind',
    humanized='io绑定',
)
# alc.shortcut(
#     '(?i:io)(?i:查询|查|query|stats)',
#     command='tstats TETR.IO query',
#     humanized='io查',
# )
alc.shortcut(
    '(?i:io)(?i:记录|record)(?i:40l)',
    command='tstats TETR.IO record --40l',
    humanized='io记录40l',
)
alc.shortcut(
    '(?i:io)(?i:记录|record)(?i:blitz)',
    command='tstats TETR.IO record --blitz',
    humanized='io记录blitz',
)
# alc.shortcut(
#     r'(?i:io)(?i:段位|段|rank)\s*(?P<rank>[a-zA-Z+-]{0,2})',
#     command='tstats TETR.IO rank {rank}',
#     humanized='iorank',
#     fuzzy=False,
#     wrapper=rank_wrapper,
# )
alc.shortcut(
    '(?i:io)(?i:配置|配|config)',
    command='tstats TETR.IO config',
    humanized='io配置',
)

# alc.shortcut(
#     'fkosk',
#     command='tstats TETR.IO query',
#     arguments=['我'],
#     fuzzy=False,
#     humanized='An Easter egg!',
# )

# add_block_handlers(alc.assign('TETRIO.query'))

# from . import bind, config, list, query, rank, record
from . import bind, config, record  # noqa: E402

__all__ = [
    'bind',
    'config',
    # 'list',
    # 'query',
    # 'rank',
    'record',
]
