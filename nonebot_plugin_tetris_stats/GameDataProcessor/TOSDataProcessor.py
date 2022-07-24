from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, MessageEvent
from nonebot.matcher import Matcher

from typing import Any
from asyncio import gather
from re import I

from ..Utils.Request import request

from ..Utils.MessageAnalyzer import *
from ..Utils.SQL import *

tosStats = on_regex(pattern=r'^tos查|^tostats|^茶服查|^茶服stats',
                    flags=I, permission=GROUP)


@tosStats.handle()
async def _(event: MessageEvent, matcher: Matcher):
    decodedMessage = await handleStatsQueryMessage(message=event.raw_message, gameType='TOS')
    if decodedMessage[0] is None:
        await matcher.finish(decodedMessage[1][0])
    elif decodedMessage[0] == 'AT' or decodedMessage[0] == 'QQ':
        if decodedMessage[1][1] == event.self_id:
            await matcher.finish(message='不能查询bot的信息')
        message = await generateMessage(teaID=decodedMessage[1][1])
    elif decodedMessage[0] == 'ME':
        message = await generateMessage(teaID=event.sender.user_id)
    elif decodedMessage[0] == 'Name':
        message = await generateMessage(userName=decodedMessage[1][1])
    await matcher.finish(message=message)


async def getUserInfo(userName: str = None, teaID: int = None) -> tuple[bool, bool, dict[str, Any]]:
    # 获取用户信息
    if userName is not None and teaID is None:
        userDataUrl = f'https://teatube.cn:8888/getUsernameInfo?username={userName}'
    elif userName is None and teaID is not None:
        userDataUrl = f'https://teatube.cn:8888/getTeaIdInfo?teaId={teaID}'
    else:
        raise ValueError(
            '[TETRIS STATS] TOSDataProcessing.getUserInfo: 预期外行为，请上报GitHub')
    return await request(Url=userDataUrl)


async def getUserData(userName: str = None, teaID: int = None, otherParameter: str = '') -> tuple[bool, bool, dict[str, Any]]:
    # 获取用户数据
    if userName is not None and teaID is None:
        userDataUrl = f'https://teatube.cn:8888/getProfile?id={userName}{otherParameter}'
    elif userName is None and teaID is not None:
        userDataUrl = f'https://teatube.cn:8888/getProfile?id={teaID}{otherParameter}'
    else:
        raise ValueError(
            '[TETRIS STATS] TOSDataProcessing.getUserData: 预期外行为，请上报GitHub')
    return await request(Url=userDataUrl)


async def getRankStats(userInfo: dict) -> dict[str, bool | float]:
    # 获取Rank数据
    rankStats: dict[str, bool | float] = {}
    if int(userInfo['data']['rankedGames']) == 0:
        rankStats['Played'] = False
    else:
        rankStats['Played'] = True
        rankStats['Rating'] = round(
            float(userInfo['data']['ratingNow']), 2)
        rankStats['RD'] = round(float(userInfo['data']['rdNow']), 2)
        rankStats['Vol'] = round(float(userInfo['data']['volNow']), 3)
    return rankStats


async def getGameData(userData: dict) -> dict[str, bool | int | float]:
    # 获取游戏数据
    gameData: dict[str, bool | int | float] = {}
    if userData['data'] == []:
        gameData['Played'] = False
    else:
        gameData['Played'] = True
        weightedTotalLpm = weightedTotalApm = weightedTotalAdpm = weightedTotalTime = num = 0
        for i in userData['data']:
            # 排除单人局和时间为0的游戏
            if i['num_players'] == 1 or i['time'] == 0:
                continue
            # 茶：不计算没挖掘的局，即使apm和lpm也如此
            if i['dig'] is None:
                break
            # 加权计算
            time = i['time'] / 1000
            lpm = 24 * (i['pieces'] / time)
            apm = (i['attack'] / time) * 60
            adpm = ((i['attack'] + i['dig']) / time) * 60
            weightedTotalLpm += lpm * time
            weightedTotalApm += apm * time
            weightedTotalAdpm += adpm * time
            weightedTotalTime += time
            num += 1
            if num == 50:
                break
        gameData['NUM'] = num
        gameData['LPM'] = round((weightedTotalLpm / weightedTotalTime), 2)
        gameData['APM'] = round((weightedTotalApm / weightedTotalTime), 2)
        gameData['ADPM'] = round((weightedTotalAdpm / weightedTotalTime), 2)
        gameData['PPS'] = round((gameData['LPM'] / 24), 2)
        gameData['APL'] = round((gameData['APM'] / gameData['LPM']), 2)
        gameData['ADPL'] = round((gameData['ADPM'] / gameData['LPM']), 2)
        gameData['VS'] = round((gameData['ADPM'] / 60 * 100), 2)
        # TODO: 如果有效局数不满50, 没有无dig信息的局, 且userData['data']内有50个局, 则继续往前获取信息
    return gameData


async def getPBData(userInfo: dict) -> dict[str, bool | float | str]:
    # 获取PB数据
    PBData: dict[str, bool | float | str] = {}
    if int(userInfo['data']['PBSprint']) == 2147483647:
        PBData['Sprint'] = False
    else:
        PBData['Sprint'] = round(
            float(userInfo['data']['PBSprint']) / 1000, 2)
    if int(userInfo['data']['PBMarathon']) == 0:
        PBData['Marathon'] = False
    else:
        PBData['Marathon'] = userInfo['data']['PBMarathon']
    if int(userInfo['data']['PBChallenge']) == 0:
        PBData['Challenge'] = False
    else:
        PBData['Challenge'] = userInfo['data']['PBChallenge']
    return PBData


async def generateMessage(userName: str = None, teaID: int = None) -> str:
    # 生成消息
    userInfo, userData = await gather(getUserInfo(userName=userName, teaID=teaID), getUserData(userName=userName, teaID=teaID))
    if userInfo[0] is False:
        return f'用户信息请求失败'
    elif userInfo[1] is False:
        return f'用户信息请求错误:\n{userInfo[2]["error"]}'
    rankStats, PBData = await gather(getRankStats(userInfo[2]), getPBData(userInfo[2]))
    message = ''
    if rankStats['Played'] is False:
        message += f'用户 {userInfo[2]["data"]["name"]}（{userInfo[2]["data"]["teaId"]}）暂无段位统计数据'
    elif rankStats['Played'] is True:
        message += f'用户 {userInfo[2]["data"]["name"]} ({userInfo[2]["data"]["teaId"]}) , 段位分 {rankStats["Rating"]}±{rankStats["RD"]} ({rankStats["Vol"]}) '
    if userData[0] is False:
        message = f'{message.rstrip()}\n游戏数据请求失败'
    elif userData[1] is False:
        message = f'{message.rstrip()}\n游戏数据请求错误:\n{userData[2]["error"]}'
    else:
        gameData = await getGameData(userData[2])
        if gameData['Played'] is False:
            message += ', 暂无游戏数据'
        elif gameData['Played'] is True:
            message += f', 最近 {gameData["NUM"]} 局数据'
            message += f'\nL\'PM: {gameData["LPM"]} ( {gameData["PPS"]} pps )'
            message += f'\nAPM：{gameData["APM"]} ( x{gameData["APL"]} )'
            message += f'\nADPM：{gameData["ADPM"]} ( x{gameData["ADPL"]} ) ( {gameData["VS"]}vs )'
    if PBData['Sprint'] is not False:
        message += f'\n40L: {PBData["Sprint"]}s'
    if PBData['Marathon'] is not False:
        message += f'\nMarathon: {PBData["Marathon"]}'
    if PBData['Challenge'] is not False:
        message += f'\nChallenge: {PBData["Challenge"]}'
    return message
