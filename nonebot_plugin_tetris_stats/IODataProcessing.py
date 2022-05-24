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
        logger.error(f'[TETRIS STATS] IODataProcessing.request: 请求错误\n{e}')
        data['Status'] = False
    finally:
        return data


async def getUserData(userName: str = None, userID: str = None) -> dict[str, dict[str, any]]:
    # 获取用户数据
    if userName is not None and userID is None:
        userDataUrl = f'https://ch.tetr.io/api/users/{userName}'
        userData = await request(Url=userDataUrl)
    elif userName is None and userID is not None:
        userDataUrl = f'https://ch.tetr.io/api/users/{userID}'
        userData = await request(Url=userDataUrl)
    else:
        raise ValueError('[TETRIS STATS] IODataProcessing.getUserData: 参数错误')
    return userData


async def getSoloData(userName: str = None, userID: str = None) -> dict[str, dict[str, any]]:
    # 获取Solo数据
    if userName is not None and userID is None:
        userSoloUrl = f'https://ch.tetr.io/api/users/{userName}/records'
        soloData = await request(Url=userSoloUrl)
    elif userName is None and userID is not None:
        userSoloUrl = f'https://ch.tetr.io/api/users/{userID}/records'
        soloData = await request(Url=userSoloUrl)
    else:
        raise ValueError('[TETRIS STATS] IODataProcessing.getSoloData: 参数错误')
    return soloData


async def getUserID(userData: dict = None, userName: str = None) -> str:
    # 获取用户ID
    if userName is not None and userData is None:
        userData = await getUserData(userName=userName)
    elif userData is None and userName is None:
        raise ValueError('[TETRIS STATS] IODataProcessing.getUserID: 参数错误')
    return userData['Data']['data']['user']['_id']


async def getLeagueStats(userData: dict) -> dict[str, bool | int | str | float]:
    # 获取排位统计数据
    league = userData['Data']['data']['user']['league']
    leagueStats = {}
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


async def getSprintStats(soloData: dict) -> dict[str, bool | int | float]:
    # 获取40L统计数据
    sprintStats = {}
    if soloData['Data']['data']['records']['40l']['record'] is None:
        sprintStats['Played'] = False
    else:
        sprintStats['Played'] = True
        if soloData['Data']['data']['records']['40l']['rank'] is None:
            sprintStats['Rank'] = False
        else:
            sprintStats['Rank'] = soloData['Data']['data']['records']['40l']['rank']
        sprintStats['Time'] = round(
            soloData['Data']['data']['records']['40l']['record']['endcontext']['finalTime'] / 1000, 2)
    return sprintStats


async def getBlitzStats(soloData: dict) -> dict[str, bool | int]:
    # 获取Blitz统计数据
    blitzStats = {}
    if soloData['Data']['data']['records']['blitz']['record'] is None:
        blitzStats['Played'] = False
    else:
        blitzStats['Played'] = True
        if soloData['Data']['data']['records']['blitz']['rank'] is None:
            blitzStats['Rank'] = False
        else:
            blitzStats['Rank'] = soloData['Data']['data']['records']['blitz']['rank']
        blitzStats['Score'] = soloData['Data']['data']['records']['blitz']['record']['endcontext']['score']
    return blitzStats


async def generateMessage(userName: str = None, userID: str = None) -> str:
    # 生成消息
    userData, soloData = await gather(getUserData(userName=userName, userID=userID), getSoloData(userName=userName, userID=userID))
    if userData['Status'] is False:
        return '用户信息请求失败'
    if userData['Success'] is False:
        return f'用户信息请求错误:\n{userData["Data"]["error"]}'
    userName = userData['Data']['data']['user']['username'].upper()
    leagueStats = await getLeagueStats(userData)
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
    if soloData['Status'] is False:
        return f'{message}\nSolo统计数据请求失败'
    sprintStats = await getSprintStats(soloData)
    blitzStats = await getBlitzStats(soloData)
    if sprintStats['Played'] is True:
        message += f'\n40L: {sprintStats["Time"]}s'
        if sprintStats['Rank'] is not False:
            message += f' ( #{sprintStats["Rank"]} )'
    if blitzStats['Played'] is True:
        message += f'\nBlitz: {blitzStats["Score"]}'
        if blitzStats['Rank'] is not False:
            message += f' ( #{blitzStats["Rank"]} )'
    return message
