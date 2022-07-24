from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, MessageEvent
from nonebot.matcher import Matcher
from nonebot.log import logger

from typing import Any, Mapping
from asyncio import gather
from re import I

from ..Utils.Request import request

from ..Utils.MessageAnalyzer import handleBindMessage, handleStatsQueryMessage
from ..Utils.SQL import queryBindInfo, writeBindInfo

ioBind = on_regex(pattern=r'^io绑定|^iobind', flags=I, permission=GROUP)
ioStats = on_regex(pattern=r'^io查|^iostats', flags=I, permission=GROUP)


@ioBind.handle()
async def _(event: MessageEvent, matcher: Matcher):
    decodedMessage = await handleBindMessage(message=event.raw_message, gameType='IO')
    if decodedMessage[0] is None:
        await matcher.finish(decodedMessage[1][0])
    if decodedMessage[0] == 'ID':
        userIDStats = await checkUserID(userID=decodedMessage[1][1])
        if userIDStats[0] is False:
            await matcher.finish(userIDStats[1])
        else:
            userID = decodedMessage[1][1]
    elif decodedMessage[0] == 'Name':
        userData = await getUserData(userName=decodedMessage[1][1])
        if userData[0] is False:
            await matcher.finish('用户信息请求失败')
        elif userData[1] is False:
            await matcher.finish(f'用户信息请求错误:\n{userData[2]["error"]}')
        else:
            userID = await getUserID(userData=userData[2])
    if event.sender.user_id is None:  # 理论上是不会有None出现的，ide快乐行属于是（
        logger.error('获取QQ号失败')
        await matcher.finish('获取QQ号失败')
    await matcher.finish(await writeBindInfo(QQNumber=event.sender.user_id, user=userID, gameType='IO'))


@ioStats.handle()
async def _(event: MessageEvent, matcher: Matcher):
    decodedMessage = await handleStatsQueryMessage(message=event.raw_message, gameType='IO')
    if decodedMessage[0] is None:
        await matcher.finish(decodedMessage[1][0])
    elif decodedMessage[0] == 'AT':
        if event.is_tome() is True:
            await matcher.finish(message='不能查询bot的信息')
        bindInfo = await queryBindInfo(QQNumber=decodedMessage[1][1], gameType='IO')
        if bindInfo is None:
            message = '未查询到绑定信息'
        else:
            message = (f'* 由于无法验证绑定信息，不能保证查询到的用户为本人\n{await generateMessage(userID=bindInfo)}')
    elif decodedMessage[0] == 'ME':
        if event.sender.user_id is None:
            logger.error('获取QQ号失败')
            await matcher.finish('获取QQ号失败，请联系bot主人')
        bindInfo = await queryBindInfo(QQNumber=event.sender.user_id, gameType='IO')
        if bindInfo is None:
            message = '未查询到绑定信息'
        else:
            message = (f'* 由于无法验证绑定信息，不能保证查询到的用户为本人\n{await generateMessage(userID=bindInfo)}')
    elif decodedMessage[0] == 'ID':
        message = await generateMessage(userID=decodedMessage[1][1])
    elif decodedMessage[0] == 'Name':
        message = await generateMessage(userName=decodedMessage[1][1])
    await matcher.finish(message=message)


async def getUserData(userName: str = None, userID: str = None) -> tuple[bool, bool, dict[str, Any]]:
    # 获取用户数据
    if userName is not None and userID is None:
        userDataUrl = f'https://ch.tetr.io/api/users/{userName}'
    elif userName is None and userID is not None:
        userDataUrl = f'https://ch.tetr.io/api/users/{userID}'
    else:
        raise ValueError(
            '[TETRIS STATS] IODataProcessing.getUserData: 预期外行为，请上报GitHub')
    return await request(Url=userDataUrl)


async def getSoloData(userName: str = None, userID: str = None) -> tuple[bool, bool, dict[str, Any]]:
    # 获取Solo数据
    if userName is not None and userID is None:
        userSoloUrl = f'https://ch.tetr.io/api/users/{userName}/records'
    elif userName is None and userID is not None:
        userSoloUrl = f'https://ch.tetr.io/api/users/{userID}/records'
    else:
        raise ValueError(
            '[TETRIS STATS] IODataProcessing.getSoloData: 预期外行为，请上报GitHub')
    return await request(Url=userSoloUrl)


async def getUserID(userData: dict) -> str:
    return userData['data']['user']['_id']


async def checkUserID(userID: str) -> tuple[bool, str]:
    userData = await getUserData(userID=userID)
    if userData[0] is False:
        return (False, '用户信息请求失败')
    elif userData[1] is False:
        return (False, f'用户信息请求错误:\n{userData[2]["error"]}')
    elif userID == userData[2]['data']['user']['_id']:
        return (True, '')
    else:
        raise ValueError(
            '[TETRIS STATS] IODataProcessing.checkUserID: 服务器返回的userID和用户提供的不一致，这种情况理论上不应该发生，以防万一还是写一下（x')


async def getLeagueStats(userData: dict) -> dict[str, Any]:
    # 获取排位统计数据
    league = userData['data']['user']['league']
    leagueStats: dict[str, Any] = {}
    if league['gamesplayed'] == 0:
        leagueStats['Played'] = False
    else:
        leagueStats['Played'] = True
        leagueStats['PPS'] = league['pps']
        leagueStats['APM'] = league['apm']
        leagueStats['VS'] = 0 if league['vs'] is None else league['vs']
        leagueStats['Rank'] = False if league['rank'] == 'z' else league['rank'].upper()
        if league['rating'] != -1:
            leagueStats['Ranked'] = True
            leagueStats['Rating'] = round(league['rating'], 2)
            leagueStats['Glicko'] = round(league['glicko'], 2)
            leagueStats['RD'] = round(league['rd'], 2)
        else:
            leagueStats['Ranked'] = False
        leagueStats['Standing'] = league['standing']
        leagueStats['LPM'] = round((league['pps'] * 24), 2)
        leagueStats['APL'] = round(
            (leagueStats['APM'] / leagueStats['LPM']), 2)
        leagueStats['ADPM'] = round((leagueStats['VS'] * 0.6), 2)
        leagueStats['ADPL'] = round(
            (leagueStats['ADPM'] / leagueStats['LPM']), 2)
    return leagueStats


async def getSprintStats(soloData: dict) -> Mapping[str, bool | int | float]:
    # 获取40L统计数据
    sprintStats = {}
    if soloData['data']['records']['40l']['record'] is None:
        sprintStats['Played'] = False
    else:
        sprintStats['Played'] = True
        if soloData['data']['records']['40l']['rank'] is None:
            sprintStats['Rank'] = False
        else:
            sprintStats['Rank'] = soloData['data']['records']['40l']['rank']
        sprintStats['Time'] = round(
            soloData['data']['records']['40l']['record']['endcontext']['finalTime'] / 1000, 2)
    return sprintStats


async def getBlitzStats(soloData: dict) -> dict[str, Any]:
    # 获取Blitz统计数据
    blitzStats = {}
    if soloData['data']['records']['blitz']['record'] is None:
        blitzStats['Played'] = False
    else:
        blitzStats['Played'] = True
        if soloData['data']['records']['blitz']['rank'] is None:
            blitzStats['Rank'] = False
        else:
            blitzStats['Rank'] = soloData['data']['records']['blitz']['rank']
        blitzStats['Score'] = soloData['data']['records']['blitz']['record']['endcontext']['score']
    return blitzStats


async def generateMessage(userName: str = None, userID: str = None) -> str:
    # 生成消息
    userData, soloData = await gather(getUserData(userName=userName, userID=userID), getSoloData(userName=userName, userID=userID))
    if userData[0] is False:
        return '用户信息请求失败'
    elif userData[1] is False:
        return f'用户信息请求错误:\n{userData[2]["error"]}'
    userName = userData[2]['data']['user']['username'].upper()
    leagueStats = await getLeagueStats(userData[2])
    message = ''
    if leagueStats['Played'] is False:
        message += f'用户 {userName} 没有排位统计数据'
    else:
        if leagueStats['Rank'] is False and leagueStats['Ranked'] is False:
            message += f'用户 {userName} 暂未完成定级赛'
        elif leagueStats['Rank'] is False and leagueStats['Ranked'] is True:
            message += f'用户 {userName} 暂无段位, {leagueStats["Rating"]} TR'
        else:
            message += f'{leagueStats["Rank"]} 段用户 {userName} {leagueStats["Rating"]} TR (#{leagueStats["Standing"]})'
        message += f', 段位分 {leagueStats["Glicko"]}±{leagueStats["RD"]}, 最近十场的数据:' if leagueStats['Ranked'] is True else ', 最近十场的数据:'
        message += f'\nL\'PM: {leagueStats["LPM"]} ( {leagueStats["PPS"]} pps )'
        message += f'\nAPM: {leagueStats["APM"]} ( x{leagueStats["APL"]} )'
        if leagueStats["VS"] != 0:
            message += f'\nADPM: {leagueStats["ADPM"]} ( x{leagueStats["ADPL"]} ) ( {leagueStats["VS"]}vs )'
    if soloData[0] is False:
        return f'{message}\nSolo统计数据请求失败'
    elif soloData[1] is False:
        return f'{message}\nSolo统计数据请求错误:\n{soloData[2]["error"]}'
    sprintStats, blitzStats = await gather(getSprintStats(soloData[2]), getBlitzStats(soloData[2]))
    if sprintStats['Played'] is True:
        message += f'\n40L: {sprintStats["Time"]}s'
        if sprintStats['Rank'] is not False:
            message += f' ( #{sprintStats["Rank"]} )'
    if blitzStats['Played'] is True:
        message += f'\nBlitz: {blitzStats["Score"]}'
        if blitzStats['Rank'] is not False:
            message += f' ( #{blitzStats["Rank"]} )'
    return message
