from re import match

# userBind
async def handleBindMessage(message: str, gameType: str) -> dict[str, bool | str]:
    _CMD_ALIASES = {'IO': ['io绑定', 'iobind'],
                    'TOP': ['top绑定', 'topbind']}
    # 剔除命令前缀
    for i in _CMD_ALIASES[gameType]:
        if message.startswith(i):
            message = message.replace(i, '')
            message = message.strip()
            break
    if message == '' or message.isspace():
        return {'Success': False, 'Type': None, 'Message': '用户名为空'}
    else:
        return await checkName(message, gameType)

# statsQuery
async def handleStatsQueryMessage(message: str, gameType: str) -> dict[str, bool | str]:
    _CMD_ALIASES = {'IO': ['io查', 'iostats'],
                    'TOS': ['tos查', 'tostats', '茶服查', '茶服stats'],
                    'TOP': ['top查', 'topstats']}
    _ME = ['我', '自己', '私', '俺', 'me']
    message = (message.strip()).lower()
    # 剔除命令前缀
    for i in _CMD_ALIASES[gameType]:
        if message.startswith(i):
            message = message.replace(i, '')
            message = message.strip()
            break
    if message == '' or message.isspace():
        return {'Success': False, 'Type': None, 'Message': '用户名为空'}
    else:
        if message.startswith('[cq:at,qq='):
            try:
                QQNumber = int((str(message)).split(
                    '[cq:at,qq=')[1].split(']')[0])
            except ValueError:
                return {'Success': False, 'Type': None, 'Message': 'QQ号码不合法'}
            else:
                return {'Success': True, 'Type': 'AT', 'Message': None, 'QQNumber': QQNumber}
        elif message in _ME:
            return {'Success': True, 'Type': 'ME', 'Message': None}
        else:
            return await checkName(message, gameType)

async def checkName(name: str, gameType: str) -> dict[str, bool | str]:
    if gameType == 'IO':
        if match(r'^[a-f0-9]{24}$', name):
            return {'Success': True, 'Type': 'ID', 'Message': None, 'User': name}
        elif match(r'^[a-zA-Z0-9_-]{3,16}$', name):
            return {'Success': True, 'Type': 'Name', 'Message': None, 'User': name}
        else:
            return {'Success': False, 'Type': None, 'Message': '用户名不合法'}
    elif gameType == 'TOP':
        if match(r'^[a-zA-Z0-9_]{1,16}$', name):
            return {'Success': True, 'Type': 'Name', 'Message': None, 'User': name}
        else:
            return {'Success': False, 'Type': None, 'Message': '用户名不合法'}
    elif gameType == 'TOS':
        if (match(r'^(?!\.)(?!com[0-9]$)(?!con$)(?!lpt[0-9]$)(?!nul$)(?!prn$)[^\-][^\+][^\|\*\?\\\s\!:<>/$"]*[^\.\|\*\?\\\s\!:<>/$"]+$', name)
            and name.isdigit() is False
            and 2 <= len(name) <= 18):
            # 虽然我也不想这么长 但是似乎确实得这么长
            return {'Success': True, 'Type': 'Name', 'Message': None, 'User': name}
        elif name.isdigit() is True:
            return {'Success': True, 'Type': 'QQ', 'Message': None, 'QQNumber': name}
        else:
            return {'Success': False, 'Type': None, 'Message': '用户名不合法'}
