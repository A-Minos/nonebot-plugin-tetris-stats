import asyncio
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, cast

from arclet.alconna.exceptions import SpecialOptionTriggered
from nonebot.adapters import Bot, Event, Message
from nonebot_plugin_alconna import AlconnaMatcher, CommandResult
from nonebot_plugin_wait_a_minute import Hook, Status, graceful, on_shutdown_before
from nonebot_plugin_waiter import suggest as waiter_suggest  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from nonebot_plugin_alconna.extension import OutputType

AsyncHandler = Callable[..., Coroutine[Any, Any, Any]]
_confirmations: set[asyncio.Task[Message | None]] = set()


async def accepting_commands() -> bool:
    return Hook.status == Status.NOT_RUNNING_YET


@on_shutdown_before
async def cancel_pending_confirmations() -> None:
    for task in _confirmations:
        task.cancel()


async def suggest(message: str, options: list[str]) -> Message | None:
    if not await accepting_commands():
        return None

    task: asyncio.Task[Message | None] = asyncio.create_task(waiter_suggest(message, options))
    _confirmations.add(task)
    try:
        return await task
    except asyncio.CancelledError:
        # A shutdown cancels the prompt, not the surrounding command's cleanup.
        if await accepting_commands() or ((parent := asyncio.current_task()) and parent.cancelling()):
            raise
        return None
    finally:
        _confirmations.discard(task)


def register_command_output(matcher: type[AlconnaMatcher]) -> None:
    # Alconna's automatic output runs in the rule, before any protected handler.
    # Keep rendering and sending help together inside a tracked handler.
    @matcher.handle()
    @graceful(block=True)
    async def _(bot: Bot, event: Event, result: CommandResult) -> None:
        if not (output := result.output):
            return
        error = result.result.error_info
        output_type = cast('OutputType', str(error)) if isinstance(error, SpecialOptionTriggered) else 'error'
        try:
            if message := await matcher.executor.output_converter(output_type, output):
                message = await matcher.executor.send_wrapper(bot, event, message)
                await bot.send(event, await message.export(bot, fallback=True))
            else:
                await bot.send(event, output)
        except NotImplementedError:
            await bot.send(event, event.get_message().__class__(output))
        await matcher.finish()
