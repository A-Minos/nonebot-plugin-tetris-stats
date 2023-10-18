from re import I

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, MessageEvent
from nonebot.matcher import Matcher

from ...utils.exception import MessageFormatError, NeedCatchError
from ...utils.message_analyzer import handle_message
from .constant import QUERY_COMMAND
from .processor import Processor, User, identify_user_info

TOSStats = on_regex(
    pattern='|'.join([f'^{i}' for i in QUERY_COMMAND]), flags=I, permission=GROUP
)


@TOSStats.handle()
async def _(event: MessageEvent, matcher: Matcher):
    if event.is_tome():  # tome会把私聊判断为True 如果需要支持私聊则需要找其他办法
        await matcher.finish('不能查询bot的信息')
    try:
        decoded_message = handle_message(
            command_prefix=QUERY_COMMAND, message=event.raw_message
        )
    except MessageFormatError as e:
        await matcher.finish(str(e))
    if decoded_message == 'ME':
        user = User(teaid=event.get_user_id())
    elif decoded_message[0] == 'AT':
        user = User(teaid=decoded_message[1])
    else:
        try:
            user = identify_user_info(decoded_message[1])
        except MessageFormatError as e:
            await matcher.finish(str(e))
    proc = Processor(
        event_id=id(event),
        user=user,
        command_args=[],
    )
    try:
        await matcher.finish(await proc.handle_query())
    except NeedCatchError as e:
        await matcher.finish(str(e))
