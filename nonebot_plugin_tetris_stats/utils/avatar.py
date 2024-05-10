from base64 import b64encode
from io import BytesIO
from typing import Literal, overload

from nonebot_plugin_userinfo import UserInfo  # type: ignore[import-untyped]
from PIL import Image


@overload
async def get_avatar(user: UserInfo, scheme: Literal['Data URI'], default: str | None) -> str:
    """获取用户头像的指定格式

    Args:
        user (UserInfo): 要获取的用户
        scheme (Literal[&#39;Data URI&#39;]): 格式
        default (str | None): 获取不到时的默认值

    Raises:
        TypeError: Can't get avatar: 当获取不到头像并且没有设置默认值时抛出
        TypeError: Can't get avatar format: 当获取到的头像无法识别格式时抛出

    Returns:
        str: Data URI 格式的头像
    """


@overload
async def get_avatar(user: UserInfo, scheme: Literal['bytes'], default: str | None) -> bytes:
    """获取用户头像的指定格式

    Args:
        user (UserInfo): 要获取的用户
        scheme (Literal[&#39;bytes&#39;]): 格式
        default (str | None): 获取不到时的默认值

    Returns:
        bytes: bytes 格式的头像
    """


async def get_avatar(user: UserInfo, scheme: Literal['Data URI', 'bytes'], default: str | None) -> str | bytes:
    if user.user_avatar is None:
        if default is None:
            raise TypeError("Can't get avatar")
        return default
    bot_avatar = await user.user_avatar.get_image()
    if scheme == 'Data URI':
        avatar_format = Image.open(BytesIO(bot_avatar)).format
        if avatar_format is None:
            raise TypeError("Can't get avatar format")
        return f'data:{Image.MIME[avatar_format]};base64,{b64encode(bot_avatar).decode()}'
    return bot_avatar
