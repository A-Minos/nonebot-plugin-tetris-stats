from re import match, sub


async def handleBindMessage(message: str, gameType: str) -> tuple[str | None, tuple]:
    '''返回值为tuple[gameType, tuple[message, user]]'''
    _CMD_ALIASES = {'IO': ['io绑定', 'iobind'],
                    'TOP': ['top绑定', 'topbind']}
    # 剔除命令前缀
    for i in _CMD_ALIASES[gameType]:
        if message.startswith(i):
            message = sub(rf'(?i){i}', '', message)
            message = message.strip()
            break
    else:
        raise ValueError(
            '[TETRIS STATS] MessageAnalyzer.handleBindMessage: 预期外行为，请上报GitHub')
    if message == '' or message.isspace():
        return (None, ('用户名为空', None))
    else:
        return await checkName(message, gameType)


async def handleStatsQueryMessage(message: str, gameType: str) -> tuple[str | None, tuple]:
    '''返回值为tuple[gameType, tuple[message, user]]'''
    _CMD_ALIASES = {'IO': ['io查', 'iostats'],
                    'TOS': ['tos查', 'tostats', '茶服查', '茶服stats'],
                    'TOP': ['top查', 'topstats']}
    _ME = ['我', '自己', '我等', '卑人', '愚', '老身', '爷', '老娘', '本姑娘', '本大爷',
           '鄙人', '寡人', '小生', '贫僧', '本人', '孤', '吾', '俺', '咱', '私', 'me']
    # 剔除命令前缀
    for i in _CMD_ALIASES[gameType]:
        if message.startswith(i):
            message = sub(rf'(?i){i}', '', message)
            message = message.strip()
            break
    if message == '' or message.isspace():
        return (None, ('用户名为空', None))
    else:
        if message.startswith('[CQ:at,qq='):
            try:
                user = int(str(message).split('[CQ:at,qq=')[1].split(']')[0])
            except ValueError:
                return (None, ('QQ号码不合法', None))
            else:
                return ('AT', (None, user))
        elif message in _ME:
            # 会不会有人叫本姑娘 本大爷这种或许可以成为id的名字呢
            # TODO: 在判断是否可能是查自己的情况的时候 也去判断是否能成立为一个UserName
            return ('ME', (None, None))
        else:
            return await checkName(message, gameType)


async def checkName(name: str, gameType: str) -> tuple[str | None, tuple]:
    '''返回值为tuple[gameType, tuple[message, user]]'''
    if gameType == 'IO':
        if match(r'^[a-f0-9]{24}$', name):
            return ('ID', (None, name))
        elif match(r'^[a-zA-Z0-9_-]{3,16}$', name):
            return ('Name', (None, name.lower()))
        else:
            return (None, ('用户名不合法', None))
    elif gameType == 'TOP':
        if match(r'^[a-zA-Z0-9_]{1,16}$', name):
            return ('Name', (None, name))
        else:
            return (None, ('用户名不合法', None))
    elif gameType == 'TOS':
        if (match(r'^(?!\.)(?!com[0-9]$)(?!con$)(?!lpt[0-9]$)(?!nul$)(?!prn$)[^\-][^\+][^\|\*\?\\\s\!:<>/$"]*[^\.\|\*\?\\\s\!:<>/$"]+$', name)
            and name.isdigit() is False
                and 2 <= len(name) <= 18):
            # 虽然我也不想这么长 但是似乎确实得这么长
            return ('Name', (None, name))
        elif name.isdigit() is True:
            return ('QQ', (None, name))
        else:
            return (None, ('用户名不合法', None))
    else:
        return (None, ('游戏类型错误', None))
