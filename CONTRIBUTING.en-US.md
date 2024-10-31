# How to Contribute?

## Setting Up the Environment

### For Developers with Basic Python Knowledge

First, you need install [uv](https://docs.astral.sh/uv/).  
Then:

```bash
# Set up the basic Python environment
uv python install 3.10

# Clone the repository
git clone https://github.com/A-Minos/nonebot-plugin-tetris-stats.git
cd nonebot-plugin-tetris-stats

# Install dependencies
uv sync
```

## Development

### Code Development

1. For static code analysis, use [ruff](https://docs.astral.sh/ruff/). You can install the corresponding plugin for your IDE or use the command line with `ruff check ./nonebot_plugin_tetris_stats/` to check the code.
2. For code formatting, use [ruff](https://docs.astral.sh/ruff/). You can install the corresponding plugin for your IDE or use the command line with `ruff format ./nonebot_plugin_tetris_stats/` to format the code.
3. For type checking, use both [basedpyright](https://docs.basedpyright.com/latest/) and [mypy](https://www.mypy-lang.org/). You can install the corresponding plugins for your IDE or use the following commands in the terminal to check the code:

```bash
# basedpyright
basedpyright ./nonebot_plugin_tetris_stats/

# mypy
mypy ./nonebot_plugin_tetris_stats/
```

### Internationalization

This project uses [Tarina](https://github.com/ArcletProject/Tarina) for internationalization support.

#### Adding a New Language

1. Navigate to the `./nonebot_plugin_tetris_stats/i18n/` directory.
2. Run `tarina-lang create {language_code}` \* Please note that the language code should preferably follow the [IETF language tag](https://en.wikipedia.org/wiki/IETF_language_tag) standard.
3. Edit the generated `./nonebot_plugin_tetris_stats/i18n/{language_code}.json` file.

#### Updating an Existing Language

1. Navigate to the `./nonebot_plugin_tetris_stats/i18n/` directory.
2. Edit the corresponding `./nonebot_plugin_tetris_stats/i18n/{language_code}.json` file.

#### Adding New Entries

1. Navigate to the `./nonebot_plugin_tetris_stats/i18n/` directory.
2. Edit the `.template.json` file.
3. Run `tarina-lang schema && tarina-lang model`.
4. Modify the language files, adding new entries at least to `en-US.json`.
