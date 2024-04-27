from math import ceil, floor

from jinja2 import Environment, FileSystemLoader

TR_MIN = 0
TR_MAX = 25000

data = [
    [1687363200000, 24510],
    [1687449600000, 24560],
    [1687536000000, 24520],
    [1687622400000, 24550],
    [1687708800000, 25000],
    [1687795200000, 24450],
    [1687821600000, 24210],
    [1687881600000, 24530],
    [1687968000000, 24520],
    [1688054400000, 24550],
    [1688140800001, 25000],
]


def get_value_bounds(values: list[int | float]) -> tuple[int, int]:
    value_max = 10 * ceil(max(values) / 10)
    value_min = 10 * floor(min(values) / 10)
    return value_max, value_min


def get_split(value_max: int, value_min: int) -> tuple[int, int]:
    offset = 0
    overflow = 0

    while True:
        if (new_max_value := value_max + offset + overflow) > TR_MAX:
            overflow -= 1
            continue
        if (new_min_value := value_min - offset + overflow) < TR_MIN:
            overflow += 1
            continue
        if ((new_max_value - new_min_value) / 40).is_integer():
            split_value = int((value_max + offset - (value_min - offset)) / 4)
            break
        offset += 1
    return split_value, offset + overflow


value_max, value_min = get_value_bounds([i[1] for i in data])
split_value, offset = get_split(value_max, value_min)

env = Environment(loader=FileSystemLoader('nonebot_plugin_tetris_stats/templates'))


template = env.get_template('data-v2.j2.html')

apm = 120.73
pps = 3.07
vs = 234.49

dsps = float(format(vs / 100 - apm / 60, '.2f'))
app = float(format(apm / (60 * pps), '.2f'))
dspp = float(format(dsps / pps, '.2f'))
lpm = float(format(pps * 24, '.2f'))
adpm = float(format(vs * 0.6, '.2f'))

output = template.render(
    user_avatar='',
    md5='3fc6335e221a03dc65d4b0939575535e',
    user_name='WOSHIZHAZHA120',
    user_sign='zhazha120.cn',
    game_name='TETR.IO',
    ranking=2834.29,
    rd=60.93,
    rank='X',
    TR='24,847.98',
    global_rank=282,
    lpm=lpm,
    pps=pps,
    apm=apm,
    apl=format(apm / pps / 24, '.2f'),
    adpm=adpm,
    adpl=format(adpm / lpm, '.2f'),
    vs=vs,
    sprint='22.3s',
    blitz='389,548',
    split_value=split_value,
    offset=offset,
    value_max=value_max,
    value_min=value_min,
    data=data,
    app=app,
    dspp=dspp,
    OR=0,
    ci=format(150 * dspp + 125 * app + 50 * (vs / apm) - 25, '.2f'),
    ge=format(2 * (app * dsps / pps), '.2f'),
)

with open('./nonebot_plugin_tetris_stats/templates/test.html', 'w+', encoding='UTF-8') as file:
    file.write(output)
