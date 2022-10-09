from asyncio import gather
from typing import Any

from nonebot.log import logger

from ...utils.database import DataBase
from ...utils.message_analyzer import (
    handle_bind_message,
    handle_stats_query_message
)
from .request import Request


class Processor:
    @classmethod
    async def handle_bind(cls, message: str, qq_number: int | None) -> str:
        '''处理绑定消息'''
        decoded_message = await handle_bind_message(message=message, game_type='IO')
        if decoded_message[0] is None:
            return decoded_message[1][0]
        if decoded_message[0] == 'ID':
            user_id_stats = await cls.check_user_id(decoded_message[1][1])
            if user_id_stats[0] is False:
                return user_id_stats[1]
            user_id = decoded_message[1][1]
        elif decoded_message[0] == 'Name':
            user_data = await cls.get_user_data(user_name=decoded_message[1][1])
            if user_data[0] is False:
                return '用户信息请求失败'
            if user_data[1] is False:
                return f'用户信息请求错误:\n{user_data[2]["error"]}'
            user_id = await cls.get_user_id(user_data[2])
            if qq_number is None:  # 理论上是不会有None出现的, ide快乐行属于是（
                logger.error('获取QQ号失败')
                return '获取QQ号失败'
            return (
                await DataBase.write_bind_info(
                    qq_number=qq_number,
                    user=user_id,
                    game_type='IO'
                )
            )
        logger.error('预期外行为, 请上报GitHub')
        return '出现预期外行为，请查看后台信息'

    @classmethod
    async def handle_query(cls, message: str, qq_number: int | None):
        '''处理查询消息'''
        decoded_message = await handle_stats_query_message(message=message, game_type='IO')
        if decoded_message[0] is None:
            return decoded_message[1][0]
        if decoded_message[0] == 'AT':  # 在入口处判断是否@bot本身
            bind_info = await DataBase.query_bind_info(qq_number=decoded_message[1][1], game_type='IO')
            if bind_info is None:
                return '未查询到绑定信息'
            return f'* 由于无法验证绑定信息, 不能保证查询到的用户为本人\n{await Processor.generate_message(user_id=bind_info)}'
        if decoded_message[0] == 'ME':
            if qq_number is None:
                logger.error('获取QQ号失败')
                return '获取QQ号失败, 请联系bot主人'
            bind_info = await DataBase.query_bind_info(qq_number=qq_number, game_type='IO')
            if bind_info is None:
                return '未查询到绑定信息'
            return f'* 由于无法验证绑定信息, 不能保证查询到的用户为本人\n{await Processor.generate_message(user_id=bind_info)}'
        if decoded_message[0] == 'ID':
            return await Processor.generate_message(user_id=decoded_message[1][1])
        if decoded_message[0] == 'Name':
            return await Processor.generate_message(user_name=decoded_message[1][1])

    @classmethod
    async def get_user_data(
        cls,
        user_name: str | None = None,
        user_id: str | None = None
    ) -> tuple[bool, bool, dict[str, Any]]:
        '''获取用户数据'''
        if user_name is not None and user_id is None:
            user_data_url = f'https://ch.tetr.io/api/users/{user_name}'
        elif user_name is None and user_id is not None:
            user_data_url = f'https://ch.tetr.io/api/users/{user_id}'
        else:
            raise ValueError('预期外行为, 请上报GitHub')
        return await Request.request(user_data_url)

    @classmethod
    async def get_solo_data(
        cls,
        user_name: str | None = None,
        user_id: str | None = None
    ) -> tuple[bool, bool, dict[str, Any]]:
        '''获取Solo数据'''
        if user_name is not None and user_id is None:
            user_solo_url = f'https://ch.tetr.io/api/users/{user_name}/records'
        elif user_name is None and user_id is not None:
            user_solo_url = f'https://ch.tetr.io/api/users/{user_id}/records'
        else:
            raise ValueError('预期外行为, 请上报GitHub')
        return await Request.request(user_solo_url)

    @classmethod
    async def get_user_id(cls, user_data: dict) -> str:
        '''获取用户ID'''
        return user_data['data']['user']['_id']

    @classmethod
    async def check_user_id(cls, user_id: str) -> tuple[bool, str]:
        '''检查用户ID是否有效 返回值为tuple[bool, message]'''
        user_data = await cls.get_user_data(user_id=user_id)
        if user_data[0] is False:
            return False, '用户信息请求失败'
        if user_data[1] is False:
            return False, f'用户信息请求错误:\n{user_data[2]["error"]}'
        if user_id == user_data[2]['data']['user']['_id']:
            return True, ''
        raise ValueError('服务器返回的userID和用户提供的不一致, 这种情况理论上不应该发生, 以防万一还是写一下（x')

    @classmethod
    async def get_league_stats(cls, user_data: dict) -> dict[str, Any]:
        '''获取排位统计数据'''
        league = user_data['data']['user']['league']
        league_stats: dict[str, Any] = {}
        if league['gamesplayed'] != 0:
            league_stats['PPS'] = league['pps']
            league_stats['APM'] = league['apm']
            league_stats['VS'] = 0 if league['vs'] is None else league['vs']
            league_stats['Rank'] = 'Z' if league['rank'] == 'z' else league['rank'].upper(
            )
            if league['rating'] == -1:
                league_stats['Rank'] = None
            else:
                league_stats['Rating'] = round(league['rating'], 2)
                league_stats['Glicko'] = round(league['glicko'], 2)
                league_stats['RD'] = round(league['rd'], 2)
            league_stats['Standing'] = league['standing']
            league_stats['LPM'] = round((league['pps'] * 24), 2)
            league_stats['APL'] = round(
                (league_stats['APM'] / league_stats['LPM']), 2)
            league_stats['ADPM'] = round((league_stats['VS'] * 0.6), 2)
            league_stats['ADPL'] = round(
                (league_stats['ADPM'] / league_stats['LPM']), 2)
        return league_stats

    @classmethod
    async def get_sprint_stats(cls, solo_data: dict) -> dict[str, Any]:
        '''获取40L统计数据'''
        sprint_stats = {}
        solo = solo_data['data']['records']['40l']
        if solo['record'] is not None:
            sprint_stats['Time'] = round(
                solo['record']['endcontext']['finalTime'] / 1000, 2)
            if solo['rank'] is not None:
                sprint_stats['Rank'] = solo['rank']
        return sprint_stats

    @classmethod
    async def get_blitz_stats(cls, solo_data: dict) -> dict[str, Any]:
        '''获取Blitz统计数据'''
        blitz_stats = {}
        blitz = solo_data['data']['records']['blitz']
        if blitz['record'] is not None:
            blitz_stats['Score'] = blitz['record']['endcontext']['score']
            if blitz['rank'] is not None:
                blitz_stats['Rank'] = blitz['rank']
        return blitz_stats

    @classmethod
    async def generate_message(
        cls,
        user_name: str | None = None,
        user_id: str | None = None
    ) -> str:
        '''生成消息'''
        user_data, solo_data = await gather(
            cls.get_user_data(user_name=user_name, user_id=user_id),
            cls.get_solo_data(user_name=user_name, user_id=user_id)
        )
        if user_data[0] is False:
            return '用户信息请求失败'
        if user_data[1] is False:
            return f'用户信息请求错误:\n{user_data[2]["error"]}'
        user_name = user_data[2]['data']['user']['username'].upper()
        league_stats = await cls.get_league_stats(user_data[2])
        message = ''
        if not league_stats:
            message += f'用户 {user_name} 没有排位统计数据'
        else:
            if league_stats['Rank'] is None:
                message += f'用户 {user_name} 暂未完成定级赛, 最近十场的数据:'
            else:
                if league_stats['Rank'] == 'Z':
                    message += f'用户 {user_name} 暂无段位, {league_stats["Rating"]} TR'
                else:
                    message += f'{league_stats["Rank"]} 段用户 {user_name} {league_stats["Rating"]} TR (#{league_stats["Standing"]})'
                message += f', 段位分 {league_stats["Glicko"]}±{league_stats["RD"]}, 最近十场的数据:'
            message += f'\nL\'PM: {league_stats["LPM"]} ( {league_stats["PPS"]} pps )'
            message += f'\nAPM: {league_stats["APM"]} ( x{league_stats["APL"]} )'
            if league_stats["VS"] != 0:
                message += f'\nADPM: {league_stats["ADPM"]} ( x{league_stats["ADPL"]} ) ( {league_stats["VS"]}vs )'
        if solo_data[0] is False:
            return f'{message}\nSolo统计数据请求失败'
        if solo_data[1] is False:
            return f'{message}\nSolo统计数据请求错误:\n{solo_data[2]["error"]}'
        sprint_stats, blitz_stats = await gather(
            cls.get_sprint_stats(solo_data[2]),
            cls.get_blitz_stats(solo_data[2])
        )
        message += f'\n40L: {sprint_stats["Time"]}s' if 'Time' in sprint_stats else ''
        message += f' ( #{sprint_stats["Rank"]} )' if 'Rank' in sprint_stats else ''
        message += f'\nBlitz: {blitz_stats["Score"]}' if 'Score' in blitz_stats else ''
        message += f' ( #{blitz_stats["Rank"]} )' if 'Rank' in blitz_stats else ''
        return message
