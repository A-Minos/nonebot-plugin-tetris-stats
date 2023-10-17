from re import I

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, Bot, MessageEvent
from nonebot.matcher import Matcher
from nonebot_plugin_orm import get_session

from ...utils.exception import MessageFormatError, NeedCatchError
from ...utils.message_analyzer import handle_message
from ...utils.recorder import Recorder
from .constant import BIND_COMMAND, QUERY_COMMAND
from .processor import Processor, User, identify_user_info, query_bind_info

IOBind = on_regex(
    pattern='|'.join([f'^{i}' for i in BIND_COMMAND]), flags=I, permission=GROUP
)
IOStats = on_regex(
    pattern='|'.join([f'^{i}' for i in QUERY_COMMAND]), flags=I, permission=GROUP
)


@IOBind.handle()
@Recorder.recorder(Recorder.receive)
async def _(event: MessageEvent, matcher: Matcher):
    try:
        decoded_message = handle_message(
            command_prefix=BIND_COMMAND, message=event.raw_message
        )
    except MessageFormatError as e:
        await matcher.finish(str(e))
    if decoded_message == 'ME' or decoded_message[0] == 'AT':
        await matcher.finish('Bind 指令不支持 AT, ME')
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
        await matcher.finish(await proc.handle_bind(source_id=event.get_user_id()))
    except NeedCatchError as e:
        await matcher.finish(str(e))


@IOStats.handle()
@Recorder.recorder(Recorder.receive)
async def _(bot: Bot, event: MessageEvent, matcher: Matcher):
    await GROUP(bot, event)
    if event.is_tome():  # tome会把私聊判断为True 如果需要支持私聊则需要找其他办法
        await matcher.finish('不能查询bot的信息')
    try:
        decoded_message = handle_message(
            command_prefix=BIND_COMMAND, message=event.raw_message
        )
    except MessageFormatError as e:
        await matcher.finish(str(e))
    message = ''
    if decoded_message == 'ME' or decoded_message[0] == 'AT':
        bind = await query_bind_info(
            session=get_session(),
            qq_number=(
                event.get_user_id() if decoded_message == 'ME' else decoded_message[1]
            ),
        )
        if bind is None:
            await matcher.finish('未查询到绑定信息')
        user = User(ID=bind.IO_id)
        message += '* 由于无法验证绑定信息, 不能保证查询到的用户为本人\n'
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
        await matcher.finish(message + await proc.handle_query())
    except NeedCatchError as e:
        await matcher.finish(str(e))
