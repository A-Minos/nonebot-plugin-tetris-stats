from re import match, sub


async def handle_bind_message(message: str, game_type: str) -> tuple[str | None, tuple]:
    '''返回值为tuple[gameType, tuple[message, user]]'''
    _cmd_aliases = {'IO': ['io绑定', 'iobind'],
                    'TOP': ['top绑定', 'topbind']}
    # 剔除命令前缀
    for i in _cmd_aliases[game_type]:
        if match(rf'(?i){i}', message):
            message = sub(rf'(?i){i}', '', message)
            message = message.strip()
            break
    else:
        raise ValueError('预期外行为, 请上报GitHub')
    if message == '' or message.isspace():
        return (None, ('用户名为空', None))
    return await check_name(message, game_type)


async def handle_stats_query_message(message: str, game_type: str) -> tuple[str | None, tuple]:
    '''返回值为tuple[gameType, tuple[message, user]]'''
    _cmd_aliases = {'IO': ['io查', 'iostats'],
                    'TOS': ['tos查', 'tostats', 'tosstats', '茶服查', '茶服stats'],
                    'TOP': ['top查', 'topstats']}
    _me = ['我', '自己', '我等', '卑人', '愚', '老身', '爷', '老娘', '本姑娘', '本大爷', '鄙人', '寡人',
           '小生', '贫僧', '本人', '孤', '吾', '俺', '咱', '私', 'me', '洒家', '在下', '偶', '人家',
           '本小姐', '老夫', '老子', '朕', '本尊', '僕', '拙者', '妾', '儂', '自分', '吾輩', '我輩', '某',
           '己等', '俺等', '此方', '哥', '姐', '劳资', '本宝宝', '余', '本喵',  'watashi',  'i', 'myself',
           'self', 'oneself']
    # 剔除命令前缀
    for i in _cmd_aliases[game_type]:
        if match(rf'(?i){i}', message):
            message = sub(rf'(?i){i}', '', message)
            message = message.strip()
            break
    if message == '' or message.isspace():
        return (None, ('用户名为空', None))
    if message.startswith('[CQ:at,qq='):
        try:
            user = int(str(message).split('[CQ:at,qq=')[1].split(']')[0])
        except ValueError:
            return (None, ('QQ号码不合法', None))
        else:
            return ('AT', (None, user))
    elif message in _me:
        # 会不会有人叫本姑娘 本大爷这种或许可以成为id的名字呢
        # TODO: 在判断是否可能是查自己的情况的时候 也去判断是否能成立为一个UserName
        return ('ME', (None, None))
    else:
        return await check_name(message, game_type)


async def check_name(name: str, game_type: str) -> tuple[str | None, tuple]:
    '''返回值为tuple[gameType, tuple[message, user]]'''
    if game_type == 'IO':
        if match(r'^[a-f0-9]{24}$', name):
            return ('ID', (None, name))
        if match(r'^[a-zA-Z0-9_-]{3,16}$', name):
            return ('Name', (None, name.lower()))
        return (None, ('用户名不合法', None))
    if game_type == 'TOP':
        if match(r'^[a-zA-Z0-9_]{1,16}$', name):
            return ('Name', (None, name))
        return (None, ('用户名不合法', None))
    if game_type == 'TOS':
        if (match(r'^(?!\.)(?!com[0-9]$)(?!con$)(?!lpt[0-9]$)(?!nul$)(?!prn$)[^\-][^\+][^\|\*\?\\\s\!:<>/$"]*[^\.\|\*\?\\\s\!:<>/$"]+$', name)
            and name.isdigit() is False
                and 2 <= len(name) <= 18):
            # 虽然我也不想这么长 但是似乎确实得这么长
            return ('Name', (None, name))
        if name.isdigit() is True:
            return ('QQ', (None, name))
        return (None, ('用户名不合法', None))
    return (None, ('游戏类型错误', None))
