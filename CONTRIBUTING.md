# 我该如何参与开发?

## 配置环境

### 对于有一定 Python 基础的开发者

首先你需要 [Python **3.10**](https://www.python.org/) 以及 [Poetry](https://python-poetry.org/)。  
然后你需要使用`git clone`命令将本仓库克隆到本地，然后使用`poetry install --sync`安装依赖。

### 对于基础不是很好的开发者

以下是**我认为的**最佳实践:

```bash
# 安装 uv
# 请参考 https://docs.astral.sh/uv/getting-started/installation/

# 配置基础 Python 环境
uv python install 3.10
uv tool install poetry

# 克隆仓库
git clone https://github.com/A-Minos/nonebot-plugin-tetris-stats.git
cd nonebot-plugin-tetris-stats

# 安装依赖
uv run --no-project --python 3.10 poetry env use python
poetry install --sync
```

## 开发

### 代码开发

1. 代码静态检查使用 [ruff](https://docs.astral.sh/ruff/)，你可以为你的ide安装对应插件来使用，也可以在命令行使用`ruff check ./nonebot_plugin_tetris_stats/`来检查代码。
2. 代码格式化使用 [ruff](https://docs.astral.sh/ruff/)，你可以为你的ide安装对应插件来使用，也可以在命令行使用`ruff format ./nonebot_plugin_tetris_stats/`来格式化代码。
3. 类型检查同时使用 [basedpyright](https://docs.basedpyright.com/latest/) 和 [mypy](https://www.mypy-lang.org/)，你可以为你的ide安装对应插件来使用。
也可以在命令行使用下面的命令来检查代码:

```bash
# basedpyright
basedpyright ./nonebot_plugin_tetris_stats/

# mypy
mypy ./nonebot_plugin_tetris_stats/
```

### 国际化

本项目使用 [Tarina](https://github.com/ArcletProject/Tarina) 提供国际化支持。

#### 添加新的语言

1. 进入 `./nonebot_plugin_tetris_stats/i18n/` 目录。
2. 运行 `tarina-lang create {语言代码}` * 请注意，语言代码最好符合 [IETF语言标签](https://zh.wikipedia.org/wiki/IETF%E8%AF%AD%E8%A8%80%E6%A0%87%E7%AD%BE) 的规范。
3. 编辑生成的 `./nonebot_plugin_tetris_stats/i18n/{语言代码}.json` 文件。

#### 更新已有语言

1. 进入 `./nonebot_plugin_tetris_stats/i18n/` 目录。
2. 编辑对应的 `./nonebot_plugin_tetris_stats/i18n/{语言代码}.json` 文件。

#### 添加新的条目

1. 进入 `./nonebot_plugin_tetris_stats/i18n/` 目录。
2. 编辑 `.template.json` 文件。
3. 运行 `tarina-lang schema && tarina-lang model`。
4. 修改语言文件，至少为`en-US.json`添加新的条目。
