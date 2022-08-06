from typing import Any
from re import I
from lxml import etree
from pandas import read_html
import aiohttp

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, MessageEvent
from nonebot.matcher import Matcher
from nonebot.log import logger

from ..utils.message_analyzer import handle_bind_message, handle_stats_query_message
from ..utils.sql import query_bind_info, write_bind_info

TOPBind = on_regex(pattern=r'^top绑定|^topbind', flags=I, permission=GROUP)
TopStats = on_regex(pattern=r'^top查|^topstats', flags=I, permission=GROUP)


@TOPBind.handle()
async def _(event: MessageEvent, matcher: Matcher):
    decoded_message = await handle_bind_message(message=event.raw_message, game_type='TOP')
    if decoded_message[0] is None:
        await matcher.finish(decoded_message[1][0])
    elif decoded_message[0] == 'Name':
        user_data = await get_user_data(decoded_message[1][1])
        if user_data[0] is False:
            await matcher.finish('用户信息请求失败')
        else:
            if await check_user(user_data[1]) is False:
                await matcher.finish('用户不存在')
            user_name = await get_user_name(user_data[1])
    if event.sender.user_id is None:  # 理论上是不会有None出现的, ide快乐行属于是（
        logger.error('获取QQ号失败')
        await matcher.finish('获取QQ号失败')
    await matcher.finish(await write_bind_info(qq_number=event.sender.user_id, user=user_name, game_type='TOP'))


@TopStats.handle()
async def _(event: MessageEvent, matcher: Matcher):
    decoded_message = await handle_stats_query_message(message=event.raw_message, game_type='TOP')
    if decoded_message[0] is None:
        await matcher.finish(decoded_message[1][0])
    elif decoded_message[0] == 'AT':
        if event.is_tome() is True:
            await matcher.finish(message='不能查询bot的信息')
        bind_info = await query_bind_info(qq_number=decoded_message[1][1], game_type='TOP')
        if bind_info is None:
            message = '未查询到绑定信息'
        else:
            message = (f'* 由于无法验证绑定信息, 不能保证查询到的用户为本人\n{await generate_message(bind_info)}')
    elif decoded_message[0] == 'ME':
        if event.sender.user_id is None:
            logger.error('获取QQ号失败')
            await matcher.finish('获取QQ号失败, 请联系bot主人')
        bind_info = await query_bind_info(qq_number=event.sender.user_id, game_type='TOP')
        if bind_info is None:
            message = '未查询到绑定信息'
        else:
            message = (f'* 由于无法验证绑定信息, 不能保证查询到的用户为本人\n{await generate_message(bind_info)}')
    elif decoded_message[0] == 'Name':
        message = await generate_message(decoded_message[1][1])
    await matcher.finish(message=message)


async def get_user_data(user_name: str) -> tuple[bool, str]:
    '''获取用户信息'''
    url = f'http://tetrisonline.pl/top/profile.php?user={user_name}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return (True, await resp.text())
    except aiohttp.client_exceptions.ClientConnectorError as error:
        logger.error(error)
        return (False, '')


async def check_user(user_data: str) -> bool:
    '''如果用户存在返回True, 如果用户不存在返回False'''
    return user_data.find('user not found!') == -1


async def get_user_name(user_data: str) -> str:
    '''获取用户名'''
    data = etree.HTML(user_data).xpath('//div[@class="mycontent"]/h1/text()')
    if isinstance(data, list):
        return str(data[0]).replace('\'s profile', '')
    raise TypeError('预期外行为, 请上报GitHub')


async def get_game_stats(user_data: str) -> dict[str, dict[str, Any]]:
    '''获取游戏统计数据'''
    game_stats: dict[str, Any] = {'24H': {}, 'All': {}}
    html = etree.HTML(user_data)
    data = html.xpath('//div[@class="mycontent"]//text()')
    if isinstance(data, list):
        for i in data:
            if not isinstance(i, str):
                i = str(i)
            i = i.strip()
            if i.startswith('lpm:'):
                game_stats['24H']['LPM'] = i.replace('lpm:', '').strip()
            if i.startswith('apm:'):
                game_stats['24H']['APM'] = i.replace('apm:', '').strip()
            if 'LPM' in game_stats['24H'] and 'APM' in game_stats['24H']:
                break
    else:
        raise TypeError('预期外行为, 请上报GitHub')
    # 如果没有24H统计数据
    if game_stats['24H'].get('LPM') in [None, ''] or game_stats['24H'].get('APM') in [None, '']:
        game_stats['24H'].pop('LPM', None)
        game_stats['24H'].pop('APM', None)
    else:
        game_stats['24H']['PPS'] = round(
            float(game_stats['24H']['LPM']) / 24, 2)
        game_stats['24H']['APL'] = round(
            float(game_stats['24H']['APM']) / float(game_stats['24H']['LPM']), 2)
        game_stats['24H']['LPM'] = round(float(game_stats['24H']['LPM']), 2)
        game_stats['24H']['APM'] = round(float(game_stats['24H']['APM']), 2)
    table = html.xpath('//table')
    if isinstance(table, list):
        if isinstance(table[0], etree._Element):
            stats_table = etree.tostring(table[0], encoding='utf-8').decode()
            df = read_html(stats_table, encoding='utf-8', header=0)[0]
            results = df.T.to_dict().values()
            if results:
                game_stats['All']['LPM'] = 0
                game_stats['All']['APM'] = 0
                for i in results:
                    if isinstance(i, dict):
                        game_stats['All']['LPM'] += i['lpm']
                        game_stats['All']['APM'] += i['apm']
                game_stats['All']['LPM'] = game_stats['All']['LPM'] / \
                    len(results)
                game_stats['All']['APM'] = game_stats['All']['APM'] / \
                    len(results)
                game_stats['All']['PPS'] = round(
                    game_stats['All']['LPM'] / 24, 2)
                game_stats['All']['APL'] = round(
                    float(game_stats['All']['APM']) / float(game_stats['All']['LPM']), 2)
                game_stats['All']['LPM'] = round(
                    float(game_stats['All']['LPM']), 2)
                game_stats['All']['APM'] = round(
                    float(game_stats['All']['APM']), 2)
    else:
        raise TypeError('预期外行为, 请上报GitHub')
    return game_stats


async def generate_message(user_name: str) -> str:
    '''生成消息'''
    user_data = await get_user_data(user_name)
    if user_data[0] is False:
        return '用户信息请求失败'
    if await check_user(user_data[1]) is False:
        return '用户不存在'
    user_name = await get_user_name(user_data[1])
    game_stats = await get_game_stats(user_data[1])
    message = ''
    if game_stats['24H'] and game_stats['All']:
        message += f'用户 {user_name} 24小时内统计数据为: '
        message += f'\nL\'PM: {game_stats["24H"]["LPM"]} ( {game_stats["24H"]["PPS"]} pps )'
        message += f'\nAPM: {game_stats["24H"]["APM"]} ( x{game_stats["24H"]["APL"]} )'
        message += '\n历史统计数据为: '
        message += f'\nL\'PM: {game_stats["All"]["LPM"]} ( {game_stats["All"]["PPS"]} pps )'
        message += f'\nAPM: {game_stats["All"]["APM"]} ( x{game_stats["All"]["APL"]} )'
    elif game_stats['24H'] and not game_stats['All']:
        message += f'用户 {user_name} 24小时内统计数据为: '
        message += f'\nL\'PM: {game_stats["24H"]["LPM"]} ( {game_stats["24H"]["PPS"]} pps )'
        message += f'\nAPM: {game_stats["24H"]["APM"]} ( x{game_stats["24H"]["APL"]} )'
        message += '\n暂无历史统计数据'
        message += '\n( 这理论上不该存在, 如果你看到了, 请联系bot主人查看后台'
        logger.error(f'老实说这个不算Error, 但是理论上不应该有, 如果你看到了这条日志, 我希望你能来Github发个issue（\
user_name: {user_name}\
user_data: {user_data}\
game_stats: {game_stats}')
    elif not game_stats['24H'] and game_stats['All']:
        message += f'用户 {user_name} 暂无24小时内统计数据, 历史统计数据为: '
        message += f'\nL\'PM: {game_stats["All"]["LPM"]} ( {game_stats["All"]["PPS"]} pps )'
        message += f'\nAPM: {game_stats["All"]["APM"]} ( x{game_stats["All"]["APL"]} )'
    else:
        message += f'用户 {user_name} 暂无24小时内统计数据, 暂无历史统计数据'
    return message
