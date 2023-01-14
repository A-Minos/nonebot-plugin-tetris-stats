from asyncio import gather
from typing import Any, NoReturn

from ...utils.database import DataBase
from ...utils.exception import RequestError, WhatTheFuckError
from ...utils.message_analyzer import handle_bind_message, handle_stats_query_message
from ...utils.recorder import recorder, send
from ...utils.typing import CommandType, GameType
from .request import Request


class Processor:
    def __init__(
        self, message_id: int, message: str, bot_id: str, source_id: str
    ) -> None:
        self.message_id = message_id
        self.message = message
        self.bot_id = bot_id
        self.source_id = source_id
        self.GAME_TYPE: GameType = 'IO'
        self.command_type: CommandType | None = None
        self.command_args: str | None = None
        self.user: dict[str, str | None] = {'ID': None, 'Name': None}
        self.response: dict[str, Any] = {}
        self.processed_data: dict[str, Any] = {}

    @recorder(send)
    async def handle_bind(self) -> str:
        '''处理绑定消息'''
        self.command_type = 'bind'
        decoded_message = await handle_bind_message(
            message=self.message, game_type=self.GAME_TYPE
        )
        handle_type = decoded_message[0]
        ret_message = decoded_message[1][0]
        user = decoded_message[1][1]
        if handle_type is None:
            return ret_message
        if handle_type == 'ID':
            self.user['ID'] = user
            await self.check_user_id()
        elif handle_type == 'Name':
            self.user['Name'] = user
            await self.get_user_id()
        assert isinstance(self.user['ID'], str)
        return await DataBase.write_bind_info(
            qq_number=self.source_id, user=self.user['ID'], game_type=self.GAME_TYPE
        )

    @recorder(send)
    async def handle_query(self):
        '''处理查询消息'''
        self.command_type = 'query'
        decoded_message = await handle_stats_query_message(
            message=self.message, game_type=self.GAME_TYPE
        )
        handle_type = decoded_message[0]
        ret_message = decoded_message[1][0]
        user = decoded_message[1][1]
        if handle_type is None:
            return ret_message
        if handle_type == 'AT':  # 在入口处判断是否@bot本身
            bind_info = await DataBase.query_bind_info(
                qq_number=user, game_type=self.GAME_TYPE
            )
            if bind_info is None:
                return '未查询到绑定信息'
            self.user['ID'] = bind_info
            return f'* 由于无法验证绑定信息, 不能保证查询到的用户为本人\n{await self.generate_message()}'
        if handle_type == 'ME':
            bind_info = await DataBase.query_bind_info(
                qq_number=self.source_id, game_type=self.GAME_TYPE
            )
            if bind_info is None:
                return '未查询到绑定信息'
            self.user['ID'] = bind_info
            return f'* 由于无法验证绑定信息, 不能保证查询到的用户为本人\n{await self.generate_message()}'
        if handle_type == 'ID':
            self.user['ID'] = user
            return await self.generate_message()
        if handle_type == 'Name':
            self.user['Name'] = user
            return await self.generate_message()

    async def get_user_info(self) -> tuple[str, str] | NoReturn:
        '''
        用于获取 UserName 和 UserID 的函数

        如果 UserName 和 UserID 都是 None 会 raise 一个 WhatTheFuckException（
        '''
        await self.check_user()
        user_name, user_id = self.user['Name'], self.user['ID']
        if user_name is None:
            user_name = (await self.get_user_data())['data']['user']['username']  # type: ignore[index]
        if user_id is None:
            user_id = await self.get_user_id()
        return user_name, user_id

    async def check_user(self) -> None | NoReturn:
        user_name, user_id = self.user['Name'], self.user['ID']
        if user_name is None and user_id is None:
            raise WhatTheFuckError('为什么 UserName 和 UserID 都没有')
        return None

    async def get_user_data(self) -> dict[str, Any] | NoReturn:
        '''获取用户数据'''
        if 'user_data' not in self.response:
            await self.check_user()
            user_name, user_id = self.user['Name'], self.user['ID']
            user_data_url = f'https://ch.tetr.io/api/users/{user_name or user_id}'
            req_stats, srv_stats, user_data = await Request.request(user_data_url)
            if req_stats is False:
                raise RequestError('用户信息请求失败')
            if srv_stats is False:
                raise RequestError(f'用户信息请求错误:\n{user_data["error"]}')
            self.response['user_data'] = user_data
        return self.response['user_data']

    async def get_solo_data(self) -> dict[str, Any] | NoReturn:
        '''获取Solo数据'''
        user_name, user_id = await self.get_user_info()  # type: ignore[misc]
        user_solo_url = f'https://ch.tetr.io/api/users/{user_name or user_id}/records'
        req_stats, srv_stats, user_data = await Request.request(user_solo_url)
        if 'solo_data' not in self.response:
            if req_stats is False:
                raise RequestError('Solo统计数据请求失败')
            if srv_stats is False:
                raise RequestError(f'Solo统计数据请求错误:\n{user_data["error"]}')
            self.response['solo_data'] = user_data
        return user_data

    async def get_user_id(self) -> str | NoReturn:
        '''获取用户ID'''
        if self.user['ID'] is None:
            self.user['ID'] = (await self.get_user_data())['data']['user']['_id']  # type: ignore[index]
        assert isinstance(self.user['ID'], str)
        return self.user['ID']

    async def check_user_id(self) -> None | NoReturn:
        '''
        检查用户ID是否有效

        如果无效会 raise 一个 Exception, 具体 Exception 类型以无效原因为准

        如果有效会返回 None
        '''
        _, user_id = await self.get_user_info()  # type: ignore[misc]
        if user_id != (await self.get_user_data())['data']['user']['_id']:  # type: ignore[index]
            raise WhatTheFuckError('服务器返回的userID和用户提供的不一致')
        return None  # 如果不显式写 return, mypy 会报错 原因不明

    async def get_league_stats(self) -> dict[str, Any] | NoReturn:
        '''获取排位统计数据'''
        user_data = await self.get_user_data()
        league = user_data['data']['user']['league']  # type: ignore[index]
        league_stats: dict[str, Any] = {}
        if league['gamesplayed'] != 0:
            league_stats['PPS'] = league['pps']
            league_stats['APM'] = league['apm']
            league_stats['VS'] = 0 if league['vs'] is None else league['vs']
            league_stats['Rank'] = (
                'Z' if league['rank'] == 'z' else league['rank'].upper()
            )
            if league['rating'] == -1:
                league_stats['Rank'] = None
            else:
                league_stats['Rating'] = round(league['rating'], 2)
                league_stats['Glicko'] = round(league['glicko'], 2)
                league_stats['RD'] = round(league['rd'], 2)
            league_stats['Standing'] = league['standing']
            league_stats['LPM'] = round((league['pps'] * 24), 2)
            league_stats['APL'] = round((league_stats['APM'] / league_stats['LPM']), 2)
            league_stats['ADPM'] = round((league_stats['VS'] * 0.6), 2)
            league_stats['ADPL'] = round(
                (league_stats['ADPM'] / league_stats['LPM']), 2
            )
        return league_stats

    async def get_sprint_stats(self) -> dict[str, Any] | NoReturn:
        '''获取40L统计数据'''
        solo_data = await self.get_solo_data()
        sprint_stats: dict[str, Any] = {}
        l40 = solo_data['data']['records']['40l']  # type: ignore[index]
        # l40 倒装句了属于是
        if l40['record'] is not None:
            sprint_stats['Time'] = round(
                l40['record']['endcontext']['finalTime'] / 1000, 2
            )
            if l40['rank'] is not None:
                sprint_stats['Rank'] = l40['rank']
        return sprint_stats

    async def get_blitz_stats(self) -> dict[str, Any] | NoReturn:
        '''获取Blitz统计数据'''
        solo_data = await self.get_solo_data()
        blitz_stats: dict[str, Any] = {}
        blitz = solo_data['data']['records']['blitz']  # type: ignore[index]
        if blitz['record'] is not None:
            blitz_stats['Score'] = blitz['record']['endcontext']['score']
            if blitz['rank'] is not None:
                blitz_stats['Rank'] = blitz['rank']
        return blitz_stats

    async def generate_message(self) -> str:
        '''生成消息'''
        user_name, _ = await self.get_user_info()  # type: ignore[misc]
        user_name = user_name.upper()
        league_stats = await self.get_league_stats()
        self.processed_data.update(league_stats=league_stats)
        ret_message = ''
        if not league_stats:
            ret_message += f'用户 {user_name} 没有排位统计数据'
        else:
            if league_stats['Rank'] is None:
                ret_message += f'用户 {user_name} 暂未完成定级赛, 最近十场的数据:'
            else:
                if league_stats['Rank'] == 'Z':
                    ret_message += f'用户 {user_name} 暂无段位, {league_stats["Rating"]} TR'
                else:
                    ret_message += f'{league_stats["Rank"]} 段用户 {user_name} {league_stats["Rating"]} TR (#{league_stats["Standing"]})'
                ret_message += (
                    f', 段位分 {league_stats["Glicko"]}±{league_stats["RD"]}, 最近十场的数据:'
                )
            ret_message += (
                f'\nL\'PM: {league_stats["LPM"]} ( {league_stats["PPS"]} pps )'
            )
            ret_message += f'\nAPM: {league_stats["APM"]} ( x{league_stats["APL"]} )'
            if league_stats["VS"] != 0:
                ret_message += f'\nADPM: {league_stats["ADPM"]} ( x{league_stats["ADPL"]} ) ( {league_stats["VS"]}vs )'
        try:
            sprint_stats, blitz_stats = await gather(
                self.get_sprint_stats(), self.get_blitz_stats()
            )
        except RequestError as e:
            ret_message += f'\n{str(e)}'
        else:
            self.processed_data.update(
                sprint_stats=sprint_stats, blitz_stats=blitz_stats
            )
            ret_message += (
                f'\n40L: {sprint_stats["Time"]}s' if 'Time' in sprint_stats else ''
            )
            ret_message += (
                f' ( #{sprint_stats["Rank"]} )' if 'Rank' in sprint_stats else ''
            )
            ret_message += (
                f'\nBlitz: {blitz_stats["Score"]}' if 'Score' in blitz_stats else ''
            )
            ret_message += (
                f' ( #{blitz_stats["Rank"]} )' if 'Rank' in blitz_stats else ''
            )
        return ret_message
