from nonebot.adapters import Bot


def get_platform(bot: Bot) -> str:
    try:
        from nonebot.adapters.onebot.v12 import Bot as OB12Bot

        if isinstance(bot, OB12Bot):
            return bot.platform
    except ImportError:
        pass
    try:
        from nonebot.adapters.satori import Bot as SaBot

        if isinstance(bot, SaBot):
            return bot.platform
    except ImportError:
        pass
    return bot.type
