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


output = template.render(
    user_name='C1ystal',
    user_sgin='I am not in danger, Skyler. I am the danger. A guy opens his door and gets shot...',
    game_name='TETR.IO',
    ranking=2429.21,
    rd=62.29,
    rank='U',
    TR='24,165.82',
    global_rank=743,
    lpm=48.72,
    pps=2.03,
    apm=76.87,
    apl=1.58,
    adpm=102.31,
    adpl=2.1,
    vs=170.51,
    sprint='1m 10.2s',
    blitz='289,085',
    split_value=split_value,
    offset=offset,
    value_max=value_max,
    value_min=value_min,
    data=data,
)

with open(
    './nonebot_plugin_tetris_stats/templates/test.html', 'w+', encoding='UTF-8'
) as file:
    file.write(output)
