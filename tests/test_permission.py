import pytest
from nonebot.internal.params import DependsInner
from nonebot.params import DependParam, Depends

EXPECTED_PARAMETERLESS = 3


def test_permission_plugin_is_loaded() -> None:
    from nonebot import get_plugin_by_module_name  # noqa: PLC0415

    assert get_plugin_by_module_name('nonebot_plugin_permission') is not None  # noqa: S101


def test_permission_name_is_stable() -> None:
    from nonebot_plugin_tetris_stats.permission import permission_name  # noqa: PLC0415

    assert permission_name('tetrio', 'Rank.Detail') == 'tetris.TETRIO.rank.detail'  # noqa: S101


def test_command_permission_is_default_available(monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats import permission  # noqa: PLC0415

    async def allowed() -> bool:
        return True

    dependency: DependsInner = Depends(allowed)
    calls: list[tuple[str, bool, bool]] = []

    def depends_permission(
        name: str,
        *,
        default_available: bool = True,
        prompt: bool = False,
    ) -> DependsInner:
        calls.append((name, default_available, prompt))
        return dependency

    monkeypatch.setattr(permission, 'depends_permission', depends_permission)

    assert permission.command_permission('tetrio', 'Rank.Detail') == (dependency,)  # noqa: S101
    assert calls == [('tetris.TETRIO.rank.detail', True, False)]  # noqa: S101


def test_assign_attaches_permission_to_reused_and_nested_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats import games  # noqa: PLC0415

    async def allowed() -> bool:
        return True

    dependency: DependsInner = Depends(allowed)
    calls: list[tuple[str, str]] = []

    def command_permission(game: str, command: str) -> tuple[DependsInner]:
        calls.append((game, command))
        return (dependency,)

    monkeypatch.setattr(games, 'command_permission', command_permission)
    handler_count = len(games.alc.handlers)
    try:

        @games.assign('TETRIO.query')
        async def first_handler() -> None:
            pass

        @games.assign('TETRIO.query')
        async def second_handler() -> None:
            pass

        @games.assign('TETRIO.rank.detail')
        async def nested_handler() -> None:
            pass

        assert calls == [  # noqa: S101
            ('TETRIO', 'query'),
            ('TETRIO', 'query'),
            ('TETRIO', 'rank.detail'),
        ]
        for handler in games.alc.handlers[-3:]:
            permission = handler.parameterless[-1]
            assert isinstance(permission, DependParam)  # noqa: S101
            assert permission.dependent.call is allowed  # noqa: S101
    finally:
        del games.alc.handlers[handler_count:]


def test_assign_merges_existing_parameterless_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_tetris_stats import games  # noqa: PLC0415

    async def existing() -> bool:
        return True

    async def allowed() -> bool:
        return True

    existing_dependency: DependsInner = Depends(existing)
    permission_dependency: DependsInner = Depends(allowed)

    def command_permission(_game: str, _command: str) -> tuple[DependsInner]:
        return (permission_dependency,)

    monkeypatch.setattr(games, 'command_permission', command_permission)
    handler_count = len(games.alc.handlers)
    try:

        @games.assign('TOP.query')
        @games.alc.handle(parameterless=(existing_dependency,))
        async def handler() -> None:
            pass

        parameterless = games.alc.handlers[-1].parameterless
        assert len(parameterless) == EXPECTED_PARAMETERLESS  # noqa: S101
        assert isinstance(parameterless[0], DependParam)  # noqa: S101
        assert parameterless[0].dependent.call is existing  # noqa: S101
        assert isinstance(parameterless[-1], DependParam)  # noqa: S101
        assert parameterless[-1].dependent.call is allowed  # noqa: S101
    finally:
        del games.alc.handlers[handler_count:]
