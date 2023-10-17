from re import match, sub
from typing import Literal

from .exception import MessageFormatError

ME = [
    '我',
    '自己',
    '我等',
    '卑人',
    '愚',
    '老身',
    '爷',
    '老娘',
    '本姑娘',
    '本大爷',
    '鄙人',
    '寡人',
    '小生',
    '贫僧',
    '本人',
    '孤',
    '吾',
    '俺',
    '咱',
    '私',
    'me',
    '洒家',
    '在下',
    '偶',
    '人家',
    '本小姐',
    '老夫',
    '老子',
    '朕',
    '本尊',
    '僕',
    '拙者',
    '妾',
    '儂',
    '自分',
    '吾輩',
    '我輩',
    '某',
    '己等',
    '俺等',
    '此方',
    '哥',
    '姐',
    '劳资',
    '本宝宝',
    '余',
    '本喵',
    'watashi',
    'i',
    'myself',
    'self',
    'oneself',
]


def handle_message(
    command_prefix: list[str], message: str
) -> tuple[Literal['AT', 'USER'], str] | Literal['ME']:
    for i in command_prefix:
        if match(rf'(?i){i}', message):
            message = sub(rf'(?i){i}', '', message)
            message = message.strip()
            break
    else:
        raise ValueError('预期外行为, 请上报GitHub')
    if message == '' or message.isspace():
        raise MessageFormatError('用户名为空')
    if message.startswith('[CQ:at,qq='):
        try:
            return 'AT', str(int(message.split('[CQ:at,qq=')[1].split(']')[0]))
        except ValueError as e:
            raise MessageFormatError('AT格式不正确或不支持') from e
    if message in ME:
        # 会不会有人叫本姑娘 本大爷这种或许可以成为id的名字呢
        # TODO: 在判断是否可能是查自己的情况的时候 也去判断是否能成立为一个UserName
        return 'ME'
    return 'USER', message
