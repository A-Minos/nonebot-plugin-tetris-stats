from typing import Any
from asyncio import gather
from re import I
import aiohttp

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, MessageEvent
from nonebot.matcher import Matcher
from nonebot.log import logger

from ..utils.message_analyzer import handle_stats_query_message

TOSStats = on_regex(pattern=r'^tos查|^tostats|^tosstats|^茶服查|^茶服stats',
                    flags=I, permission=GROUP)


@TOSStats.handle()
async def _(event: MessageEvent, matcher: Matcher):
    decoded_message = await handle_stats_query_message(message=event.raw_message, game_type='TOS')
    if decoded_message[0] is None:
        await matcher.finish(decoded_message[1][0])
    elif decoded_message[0] == 'AT' or decoded_message[0] == 'QQ':
        if decoded_message[1][1] == event.self_id:
            await matcher.finish(message='不能查询bot的信息')
        message = await generate_message(tea_id=decoded_message[1][1])
    elif decoded_message[0] == 'ME':
        message = await generate_message(tea_id=event.sender.user_id)
    elif decoded_message[0] == 'Name':
        message = await generate_message(user_name=decoded_message[1][1])
    await matcher.finish(message=message)


async def request(url: str) -> tuple[bool, bool, dict[str, Any]]:
    '''请求api'''
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return (True, data['success'], data)
    except aiohttp.client_exceptions.ClientConnectorError as error:
        logger.error(f'请求错误\n{error}')
        return (False, False, {})


async def get_user_info(user_name: str = None,
                        tea_id: int = None
                        ) -> tuple[bool, bool, dict[str, Any]]:
    '''获取用户信息'''
    if user_name is not None and tea_id is None:
        user_data_url = f'https://teatube.cn:8888/getUsernameInfo?username={user_name}'
    elif user_name is None and tea_id is not None:
        user_data_url = f'https://teatube.cn:8888/getTeaIdInfo?teaId={tea_id}'
    else:
        raise ValueError('预期外行为, 请上报GitHub')
    return await request(url=user_data_url)


async def get_user_data(user_name: str = None,
                        tea_id: int = None,
                        other_parameter: str = ''
                        ) -> tuple[bool, bool, dict[str, Any]]:
    '''获取用户数据'''
    if user_name is not None and tea_id is None:
        user_data_url = f'https://teatube.cn:8888/getProfile?id={user_name}{other_parameter}'
    elif user_name is None and tea_id is not None:
        user_data_url = f'https://teatube.cn:8888/getProfile?id={tea_id}{other_parameter}'
    else:
        raise ValueError('预期外行为, 请上报GitHub')
    return await request(url=user_data_url)


async def get_rank_stats(user_info: dict) -> dict[str, float]:
    '''获取Rank数据'''
    data = user_info['data']
    if int(data['rankedGames']) != 0:
        rank_stats = {}
        rank_stats['Rating'] = round(float(data['ratingNow']), 2)
        rank_stats['RD'] = round(float(data['rdNow']), 2)
        rank_stats['Vol'] = round(float(data['volNow']), 3)
    return rank_stats


async def get_game_data(user_data: dict) -> dict[str, int | float]:
    '''获取游戏数据'''
    if user_data['data'] != []:
        game_data: dict[str, int | float] = {}
        weighted_total_lpm = weighted_total_apm = weighted_total_adpm = total_time = num = 0
        for i in user_data['data']:
            # 排除单人局和时间为0的游戏
            if i['num_players'] == 1 or i['time'] == 0:
                continue
            # 茶：不计算没挖掘的局, 即使apm和lpm也如此
            if i['dig'] is None:
                continue
            # 加权计算
            time = i['time'] / 1000
            lpm = 24 * (i['pieces'] / time)
            apm = (i['attack'] / time) * 60
            adpm = ((i['attack'] + i['dig']) / time) * 60
            weighted_total_lpm += lpm * time
            weighted_total_apm += apm * time
            weighted_total_adpm += adpm * time
            total_time += time
            num += 1
            if num == 50:
                break
        if num > 0:
            game_data['NUM'] = num
            game_data['LPM'] = round((weighted_total_lpm / total_time), 2)
            game_data['APM'] = round((weighted_total_apm / total_time), 2)
            game_data['ADPM'] = round((weighted_total_adpm / total_time), 2)
            game_data['PPS'] = round((game_data['LPM'] / 24), 2)
            game_data['APL'] = round((game_data['APM'] / game_data['LPM']), 2)
            game_data['ADPL'] = round(
                (game_data['ADPM'] / game_data['LPM']), 2)
            game_data['VS'] = round((game_data['ADPM'] / 60 * 100), 2)
        # TODO: 如果有效局数不满50, 没有无dig信息的局, 且userData['data']内有50个局, 则继续往前获取信息
    return game_data


async def get_pb_data(user_info: dict) -> dict[str, float | str]:
    '''获取PB数据'''
    pb_data: dict[str, float | str] = {}
    data = user_info['data']
    if int(data['PBSprint']) != 2147483647:
        pb_data['Sprint'] = round(float(data['PBSprint']) / 1000, 2)
    if int(data['PBMarathon']) != 0:
        pb_data['Marathon'] = data['PBMarathon']
    if int(data['PBChallenge']) != 0:
        pb_data['Challenge'] = data['PBChallenge']
    return pb_data


async def generate_message(user_name: str = None, tea_id: int = None) -> str:
    '''生成消息'''
    user_info, user_data = await gather(get_user_info(user_name=user_name, tea_id=tea_id),
                                        get_user_data(user_name=user_name, tea_id=tea_id))
    if user_info[0] is False:
        return '用户信息请求失败'
    if user_info[1] is False:
        return f'用户信息请求错误:\n{user_info[2]["error"]}'
    rank_stats, pb_data = await gather(get_rank_stats(user_info[2]), get_pb_data(user_info[2]))
    message = f'用户 {user_info[2]["data"]["name"]} ({user_info[2]["data"]["teaId"]}) '
    if not rank_stats:
        message += '暂无段位统计数据'
    else:
        message += f', 段位分 {rank_stats["Rating"]}±{rank_stats["RD"]} ({rank_stats["Vol"]}) '
    if user_data[0] is False:
        message = f'{message.rstrip()}\n游戏数据请求失败'
    elif user_data[1] is False:
        message = f'{message.rstrip()}\n游戏数据请求错误:\n{user_data[2]["error"]}'
    else:
        game_data = await get_game_data(user_data[2])
        if not game_data:
            message += ', 暂无游戏数据'
        else:
            message += f', 最近 {game_data["NUM"]} 局数据'
            message += f'\nL\'PM: {game_data["LPM"]} ( {game_data["PPS"]} pps )'
            message += f'\nAPM：{game_data["APM"]} ( x{game_data["APL"]} )'
            message += f'\nADPM：{game_data["ADPM"]} ( x{game_data["ADPL"]} ) ( {game_data["VS"]}vs )'
    message += f'\n40L: {pb_data["Sprint"]}s' if 'Sprint' in pb_data else ''
    message += f'\nMarathon: {pb_data["Marathon"]}' if 'Marathon' in pb_data else ''
    message += f'\nChallenge: {pb_data["Challenge"]}' if 'Challenge' in pb_data else ''
    return message
