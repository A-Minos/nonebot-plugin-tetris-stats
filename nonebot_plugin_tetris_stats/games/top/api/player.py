from contextlib import suppress
from datetime import datetime, timezone
from io import StringIO

from lxml import etree
from pandas import read_html

from ....config.config import config
from ....db import anti_duplicate_add
from ....utils.request import Request
from ..constant import BASE_URL, USER_NAME
from .models import TOPHistoricalData
from .schemas.user import User
from .schemas.user_profile import Data, UserProfile

UTC = timezone.utc

request = Request(config.tetris.proxy.top or config.tetris.proxy.main)


class Player:
    def __init__(self, *, user_name: str, trust: bool = False) -> None:
        self.user_name = user_name
        if not trust and not USER_NAME.match(self.user_name):
            msg = 'Invalid user name'
            raise ValueError(msg)
        self.__user: User | None = None
        self._user_profile: UserProfile | None = None

    @property
    async def user(self) -> User:
        if self.__user is None:
            profile = await self.get_profile()
            self.__user = User(user_name=profile.user_name)
        return self.__user

    async def get_profile(self) -> UserProfile:
        """获取用户信息"""
        if self._user_profile is None:
            raw_user_profile = await request.request(BASE_URL / 'profile.php' % {'user': self.user_name}, is_json=False)
            self._user_profile = self._parse_profile(raw_user_profile)
            await anti_duplicate_add(
                TOPHistoricalData(
                    user_unique_identifier=(await self.user).unique_identifier,
                    api_type='User Profile',
                    data=self._user_profile,
                    update_time=datetime.now(tz=UTC),
                ),
            )
        return self._user_profile

    @staticmethod
    def _parse_profile(original_user_profile: bytes) -> UserProfile:
        html = etree.HTML(original_user_profile)
        user_name = html.xpath('//div[@class="mycontent"]/h1/text()')[0].replace("'s profile", '')
        today = None
        with suppress(ValueError):
            today = Data(
                lpm=float(str(html.xpath('//div[@class="mycontent"]/text()[3]')[0]).replace('lpm:', '').strip()),
                apm=float(str(html.xpath('//div[@class="mycontent"]/text()[4]')[0]).replace('apm:', '').strip()),
            )
        table = StringIO(
            etree.tostring(
                html.xpath('//div[@class="mycontent"]/table[@class="mytable"]')[0],
                encoding='utf-8',
            ).decode()
        )
        dataframe = read_html(table, encoding='utf-8', header=0)[0]
        total: list[Data] = []
        for _, value in dataframe.iterrows():
            total.append(Data(lpm=value['lpm'], apm=value['apm']))
        return UserProfile(user_name=user_name, today=today, total=total or None)
