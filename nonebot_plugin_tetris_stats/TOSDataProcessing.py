from nonebot.log import logger

from asyncio import gather
import aiohttp


async def request(Url: str) -> dict[str, bool | dict[str, any]]:
    # 封装请求函数
    data = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(Url) as resp:
                data['Status'] = True
                data['Data'] = await resp.json()
                data['Success'] = data['Data']['success']
    except aiohttp.client_exceptions.ClientConnectorError as e:
        logger.error(f'[TETRIS STATS] TOSDataProcessing.request: 请求错误\n{e}')
        data['Status'] = False
    finally:
        return data


async def getUserInfo(userName: str = None, teaID: int = None) -> dict[str, bool | dict[str, any]]:
    # 获取用户信息
    if userName is not None and teaID is None:
        userDataUrl = f'https://teatube.cn:8888/getUsernameInfo?username={userName}'
        userInfo = await request(Url=userDataUrl)
    elif teaID is not None and userName is None:
        userDataUrl = f'https://teatube.cn:8888/getTeaIdInfo?teaId={teaID}'
        userInfo = await request(Url=userDataUrl)
    else:
        raise ValueError('[TETRIS STATS] TOSDataProcessing.getUserInfo: 参数错误')
    return userInfo


async def getUserData(userName: str = None, teaID: int = None, otherParameter: str = '') -> dict[str, bool | dict[str, any]]:
    # 获取用户数据
    if userName is not None and teaID is None:
        userDataUrl = f'https://teatube.cn:8888/getProfile?id={userName}{otherParameter}'
        userData = await request(Url=userDataUrl)
    elif teaID is not None and userName is None:
        userDataUrl = f'https://teatube.cn:8888/getProfile?id={teaID}{otherParameter}'
        userData = await request(Url=userDataUrl)
    else:
        raise ValueError('[TETRIS STATS] TOSDataProcessing.getUserData: 参数错误')
    return userData


async def getRankStats(userInfo: dict) -> dict[str, bool | float]:
    # 获取Rank数据
    rankStats = {}
    if int(userInfo['Data']['data']['rankedGames']) == 0:
        rankStats['Played'] = False
    else:
        rankStats['Played'] = True
        rankStats['Rating'] = round(
            float(userInfo['Data']['data']['ratingNow']), 2)
        rankStats['RD'] = round(float(userInfo['Data']['data']['rdNow']), 2)
        rankStats['Vol'] = round(float(userInfo['Data']['data']['volNow']), 3)
    return rankStats


async def getGameData(userData: dict) -> dict[str, bool | int | float]:
    # 获取游戏数据
    gameData = {}
    if userData['Data']['data'] == []:
        gameData['Played'] = False
    else:
        gameData['Played'] = True
        weightedTotalLpm = weightedTotalApm = weightedTotalAdpm = weightedTotalTime = num = 0
        for i in userData['Data']['data']:
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
        # TODO: 如果有效局数不满50, 没有无dig信息的局, 且userData['Data']['data']内有50个局, 则继续往前获取信息
    return gameData


async def getPBData(userInfo: dict) -> dict[str, bool | float | str]:
    # 获取PB数据
    PBData = {}
    if int(userInfo['Data']['data']['PBSprint']) == 2147483647:
        PBData['Sprint'] = False
    else:
        PBData['Sprint'] = round(
            float(userInfo['Data']['data']['PBSprint']) / 1000, 2)
    if int(userInfo['Data']['data']['PBMarathon']) == 0:
        PBData['Marathon'] = False
    else:
        PBData['Marathon'] = userInfo['Data']['data']['PBMarathon']
    if int(userInfo['Data']['data']['PBChallenge']) == 0:
        PBData['Challenge'] = False
    else:
        PBData['Challenge'] = userInfo['Data']['data']['PBChallenge']
    return PBData


async def generateMessage(userName: str = None, teaID: int = None) -> str:
    # 生成消息
    userInfo, userData = await gather(getUserInfo(userName=userName, teaID=teaID), getUserData(userName=userName, teaID=teaID))
    if userInfo['Status'] is False:
        return f'用户信息请求失败'
    if userInfo['Success'] is False:
        return f'用户信息请求错误:\n{userInfo["Data"]["error"]}'
    rankStats = await getRankStats(userInfo)
    PBData = await getPBData(userInfo)
    message = ''
    if rankStats['Played'] is False:
        message += f'用户 {userInfo["Data"]["data"]["name"]}（{userInfo["Data"]["data"]["teaId"]}）暂无段位统计数据'
    elif rankStats['Played'] is True:
        message += f'用户 {userInfo["Data"]["data"]["name"]} ({userInfo["Data"]["data"]["teaId"]}) , 段位分 {rankStats["Rating"]}±{rankStats["RD"]} ({rankStats["Vol"]}) '
    if userData['Status'] is False:
        message = f'{message.rstrip()}\n游戏数据请求失败'
    elif userData['Status'] is True:
        gameData = await getGameData(userData)
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
