"""Pipecat Quickstart on TeleQuick — the official quickstart bot, on real phone calls.

This is pipecat-ai/pipecat-quickstart's ``bot.py`` with ONE change: instead of
the browser WebRTC/Daily transport, each engine-routed phone call gets a
``TeleQuickTransport``. The pipeline, services, aggregators, and event
handlers are the upstream file's, verbatim.

Required AI services (same as upstream):
- Deepgram (Speech-to-Text)
- OpenAI (LLM)
- Cartesia (Text-to-Speech)

Run the worker::

    uv run bot.py

then dial the number routed to your external agent.
"""

import asyncio
import os

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService

from pipecat_telequick import TeleQuickTransport, run_pipecat_worker
from telequick_agents import AgentConfig, Call

load_dotenv(override=True)


async def run_bot(transport: TeleQuickTransport, call: Call):
    logger.info(f"Starting bot for call from {call.caller_number}")

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        settings=CartesiaTTSService.Settings(
            voice="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
        ),
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        settings=OpenAILLMService.Settings(
            system_instruction=(
                "You are a friendly AI assistant on a phone call. Respond naturally "
                "and keep your answers conversational and short."
            ),
        ),
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            stt,
            user_aggregator,  # User responses
            llm,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            assistant_aggregator,  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Caller connected")
        # Phone callers expect the agent to speak first.
        context.add_message(
            {"role": "developer", "content": "Say hello and briefly introduce yourself."}
        )
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Caller disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(run_pipecat_worker(
        run_bot,
        AgentConfig.from_env(),
        on_ready=lambda: print("✓ connected — registered and awaiting calls"),
        on_disconnected=lambda e: print(f"✗ disconnected ({e}); reconnecting…"),
    ))
