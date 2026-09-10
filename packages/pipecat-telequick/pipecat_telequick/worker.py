"""Register-and-wait worker for Pipecat bots.

The Pipecat quickstart's dev runner spins one bot per WebRTC connection; this
worker spins one bot per phone call the engine routes to your agent:

    from pipecat_telequick import run_pipecat_worker
    from telequick_agents import AgentConfig

    async def bot(transport, call):        # your unmodified run_bot body
        ...

    asyncio.run(run_pipecat_worker(bot, AgentConfig.from_env()))
"""

from __future__ import annotations

from typing import Awaitable, Callable

from telequick_agents import AgentConfig, Call, serve

from .transport import TeleQuickTransport

Bot = Callable[[TeleQuickTransport, Call], Awaitable[None]]


async def run_pipecat_worker(
    bot: Bot,
    cfg: AgentConfig,
    *,
    params_factory=None,
    on_ready=None,
    on_disconnected=None,
) -> None:
    """Serve ``bot(transport, call)`` for every engine-assigned call.

    ``params_factory``: optional zero-arg callable returning fresh
    ``TransportParams`` per call (VAD analyzers and friends are stateful, so a
    shared instance across calls would leak state).

    ``on_ready`` / ``on_disconnected``: connection-lifecycle hooks forwarded to
    ``telequick_agents.serve`` — fire when the worker is registered and awaiting
    calls, and when the connection drops before a reconnect.
    """

    async def handler(call: Call) -> None:
        params = params_factory() if params_factory else None
        transport = TeleQuickTransport(call, params)
        await bot(transport, call)

    await serve(handler, cfg, on_ready=on_ready, on_disconnected=on_disconnected)
