from re import I

from nonebot import get_driver, on_regex
from nonebot.adapters.onebot.v11 import GROUP, MessageEvent
from nonebot.matcher import Matcher

from .MessageAnalyzer import *
from .SQL import *

from .IODataProcessing import generateMessage as IOgenerateMessage
from .IODataProcessing import getUserIDInfo as IOgetUserIDInfo
from .TOSDataProcessing import generateMessage as TOSgenerateMessage

driver = get_driver()


@driver.on_startup
async def startUP():
    await initDB()

ioBind = on_regex(pattern=r'^io绑定|^iobind', flags=I, permission=GROUP)
ioStats = on_regex(pattern=r'^io查|^iostats', flags=I, permission=GROUP)

tosStats = on_regex(pattern=r'^tos查|^tostats|^茶服查|^茶服stats',
                    flags=I, permission=GROUP)

topBind = on_regex(pattern=r'^top绑定|^topbind', flags=I, permission=GROUP)
topStats = on_regex(pattern=r'^top查|^topstats', flags=I, permission=GROUP)


@ioBind.handle()
async def bindIOUser(event: MessageEvent, matcher: Matcher):
    decodedMessage = await handleBindMessage(message=str(event.get_message()), gameType='IO')
    if decodedMessage['Success'] is True:
        if decodedMessage['Type'] == 'ID':
            userIDInfo = await IOgetUserIDInfo(userID=decodedMessage['User'])
            if userIDInfo['Success'] is False:
                await matcher.finish(message=userIDInfo['Message'])
        elif decodedMessage['Type'] == 'Name':
            userIDInfo = await IOgetUserIDInfo(userName=decodedMessage['User'])
            if userIDInfo['Success'] is False:
                await matcher.finish(message=userIDInfo['Message'])
        message = await writeBindInfo(QQNumber=event.sender.user_id, user=userIDInfo['userID'], gameType='IO')
    elif decodedMessage['Success'] is False:
        message = decodedMessage['Message']
    await matcher.finish(message=message)


@ioStats.handle()
async def handleIOStatsQuery(event: MessageEvent, matcher: Matcher):
    decodedMessage = await handleStatsQueryMessage(message=str(event.get_message()), gameType='IO')
    if decodedMessage['Success'] is True:
        if decodedMessage['Type'] == 'AT':
            bindInfo = await queryBindInfo(QQNumber=decodedMessage['QQNumber'], gameType='IO')
            if bindInfo['Hit'] is True:
                message = (f'* 由于无法验证绑定信息，不能保证查询到的用户为本人\n{await IOgenerateMessage(userID=bindInfo["User"])}')
            elif bindInfo['Hit'] is False:
                message = '未查询到绑定信息'
        elif decodedMessage['Type'] == 'ME':
            bindInfo = await queryBindInfo(QQNumber=event.sender.user_id, gameType='IO')
            if bindInfo['Hit'] is True:
                message = (f'* 由于无法验证绑定信息，不能保证查询到的用户为本人\n{await IOgenerateMessage(userID=bindInfo["User"])}')
            elif bindInfo['Hit'] is False:
                message = '您还没有绑定账号'
        elif decodedMessage['Type'] == 'ID':
            message = await IOgenerateMessage(userID=decodedMessage['User'])
        elif decodedMessage['Type'] == 'Name':
            message = await IOgenerateMessage(userName=decodedMessage['User'])
    elif decodedMessage['Success'] is False:
        message = decodedMessage['Message']
    await matcher.finish(message=message)


@tosStats.handle()
async def handleTOSStatsQuery(event: MessageEvent, matcher: Matcher):
    decodedMessage = await handleStatsQueryMessage(message=str(event.get_message()), gameType='TOS')
    if decodedMessage['Success'] is True:
        if decodedMessage['Type'] == 'AT' or decodedMessage['Type'] == 'QQ':
            message = await TOSgenerateMessage(teaID=decodedMessage['QQNumber'])
        elif decodedMessage['Type'] == 'ME':
            message = await TOSgenerateMessage(teaID=event.sender.user_id)
        elif decodedMessage['Type'] == 'Name':
            message = await TOSgenerateMessage(userName=decodedMessage['User'])
    elif decodedMessage['Success'] is False:
        message = decodedMessage['Message']
    await matcher.finish(message=message)


@topBind.handle()
async def bindTOPUser(event: MessageEvent, matcher: Matcher):
    await matcher.finish(message='TODO')


@topStats.handle()
async def handleTOPStatsQuery(event: MessageEvent, matcher: Matcher):
    await matcher.finish(message='TODO')
