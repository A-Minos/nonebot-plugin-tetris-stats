from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, MessageEvent
from nonebot.matcher import Matcher
from nonebot.log import logger

from typing import Any
from re import I
from lxml import etree
from pandas import read_html
import aiohttp

from ..Utils.MessageAnalyzer import handleBindMessage, handleStatsQueryMessage
from ..Utils.SQL import queryBindInfo, writeBindInfo

topBind = on_regex(pattern=r'^top绑定|^topbind', flags=I, permission=GROUP)
topStats = on_regex(pattern=r'^top查|^topstats', flags=I, permission=GROUP)


@topBind.handle()
async def _(event: MessageEvent, matcher: Matcher):
    decodedMessage = await handleBindMessage(message=event.raw_message, gameType='TOP')
    if decodedMessage[0] is None:
        await matcher.finish(decodedMessage[1][0])
    elif decodedMessage[0] == 'Name':
        userData = await getUserData(decodedMessage[1][1])
        if userData[0] is False:
            await matcher.finish('用户信息请求失败')
        else:
            if await checkUser(userData[1]) is False:
                matcher.finish('用户不存在')
            userName = await getUserName(userData[1])
    if event.sender.user_id is None:  # 理论上是不会有None出现的，ide快乐行属于是（
        logger.error('获取QQ号失败')
        await matcher.finish('获取QQ号失败')
    await matcher.finish(await writeBindInfo(QQNumber=event.sender.user_id, user=userName, gameType='TOP'))


@topStats.handle()
async def _(event: MessageEvent, matcher: Matcher):
    decodedMessage = await handleStatsQueryMessage(message=event.raw_message, gameType='TOP')
    if decodedMessage[0] is None:
        await matcher.finish(decodedMessage[1][0])
    elif decodedMessage[0] == 'AT':
        if event.is_tome() is True:
            await matcher.finish(message='不能查询bot的信息')
        bindInfo = await queryBindInfo(QQNumber=decodedMessage[1][1], gameType='TOP')
        if bindInfo is None:
            message = '未查询到绑定信息'
        else:
            message = (f'* 由于无法验证绑定信息，不能保证查询到的用户为本人\n{await generateMessage(bindInfo)}')
    elif decodedMessage[0] == 'ME':
        if event.sender.user_id is None:
            logger.error('获取QQ号失败')
            await matcher.finish('获取QQ号失败，请联系bot主人')
        bindInfo = await queryBindInfo(QQNumber=event.sender.user_id, gameType='TOP')
        if bindInfo is None:
            message = '未查询到绑定信息'
        else:
            message = (f'* 由于无法验证绑定信息，不能保证查询到的用户为本人\n{await generateMessage(bindInfo)}')
    elif decodedMessage[0] == 'Name':
        message = await generateMessage(decodedMessage[1][1])
    await matcher.finish(message=message)


async def getUserData(userName: str) -> tuple[bool, str]:
    Url = f'http://tetrisonline.pl/top/profile.php?user={userName}'
    # 因为top查数据没有api 所以不得不再写一次请求（
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(Url) as resp:
                return (True, await resp.text())
    except aiohttp.client_exceptions.ClientConnectorError as e:
        logger.error(e)
        return (False, '')


async def checkUser(userData: str) -> bool:
    '''如果用户存在返回True，如果用户不存在返回False'''
    return False if userData.find('user not found!') != -1 else True


async def getUserName(userData: str) -> str:
    return etree.HTML(userData).xpath('//div[@class="mycontent"]/h1/text()')[0].replace('\'s profile', '')


async def getGameStats(userData: str) -> dict[str, Any]:
    gameStats = {}
    html = etree.HTML(userData)
    for i in html.xpath('//div[@class="mycontent"]//text()'):
        i = i.strip()
        if i.startswith('lpm:'):
            gameStats['24HStats'] = True
            gameStats['24HLPM'] = i.replace('lpm:', '').strip()
        elif i.startswith('apm:'):
            gameStats['24HStats'] = True
            gameStats['24HAPM'] = i.replace('apm:', '').strip()
        if '24HLPM' in gameStats and '24HAPM' in gameStats:
            break
    # 如果没有24H统计数据
    if gameStats.get('24HLPM') in [None, ''] or gameStats.get('24HAPM') in [None, '']:
        gameStats['24HStats'] = False
    else:
        gameStats['24HPPS'] = round(float(gameStats['24HLPM']) / 24, 2)
        gameStats['24HAPL'] = round(
            float(gameStats['24HAPM']) / float(gameStats['24HLPM']), 2)
        gameStats['24HLPM'] = round(float(gameStats['24HLPM']), 2)
        gameStats['24HAPM'] = round(float(gameStats['24HAPM']), 2)
    statsTable = html.xpath('//table')
    statsTable = etree.tostring(statsTable[0], encoding='utf-8').decode()
    df = read_html(statsTable, encoding='utf-8', header=0)[0]
    results = list(df.T.to_dict().values())
    if results != []:
        gameStats['AllStats'] = True
        gameStats['AllLPM'] = 0
        gameStats['AllAPM'] = 0
        for i in results:
            gameStats['AllLPM'] += i['lpm']
            gameStats['AllAPM'] += i['apm']
        gameStats['AllLPM'] = gameStats['AllLPM'] / len(results)
        gameStats['AllAPM'] = gameStats['AllAPM'] / len(results)
        gameStats['AllPPS'] = round(gameStats['AllLPM'] / 24, 2)
        gameStats['AllAPL'] = round(
            float(gameStats['AllAPM']) / float(gameStats['AllLPM']), 2)
        gameStats['AllLPM'] = round(float(gameStats['AllLPM']), 2)
        gameStats['AllAPM'] = round(float(gameStats['AllAPM']), 2)
    else:
        gameStats['AllStats'] = False
    return gameStats


async def generateMessage(userName: str) -> str:
    userData = await getUserData(userName)
    if userData[0] is False:
        return '用户信息请求失败'
    if await checkUser(userData[1]) is False:
        return '用户不存在'
    userName = await getUserName(userData[1])
    gameStats = await getGameStats(userData[1])
    if gameStats['24HStats'] is False and gameStats['AllStats'] is False:
        message = f'用户 {userName} 暂无24小时内统计数据, 暂无历史统计数据'
    elif gameStats['24HStats'] is True and gameStats['AllStats'] is False:
        message = f'用户 {userName} 24小时内统计数据为: \nL\'PM: {gameStats["24HLPM"]} ( {gameStats["24HPPS"]} pps )\nAPM: {gameStats["24HAPM"]} ( x{gameStats["24HAPL"]} )\n暂无历史统计数据\n（这真的存在吗'
    elif gameStats['24HStats'] is False and gameStats['AllStats'] is True:
        message = f'用户 {userName} 暂无24小时内统计数据, 历史统计数据为: \nL\'PM: {gameStats["AllLPM"]} ( {gameStats["AllPPS"]} pps )\nAPM: {gameStats["AllAPM"]} ( x{gameStats["AllAPL"]} )'
    else:
        message = f'用户 {userName} 24小时内统计数据为: \nL\'PM: {gameStats["24HLPM"]} ( {gameStats["24HPPS"]} pps )\nAPM: {gameStats["24HAPM"]} ( x{gameStats["24HAPL"]} )\n历史统计数据为: \nL\'PM: {gameStats["AllLPM"]} ( {gameStats["AllPPS"]} pps )\nAPM: {gameStats["AllAPM"]} ( x{gameStats["AllAPL"]} )'
    return message
