"""TeleQuick transport for Pipecat.

Drop-in replacement for Pipecat's Daily / SmallWebRTC / websocket transports:
your pipeline (`transport.input() … transport.output()`), services, and event
handlers stay exactly as the Pipecat quickstart wrote them — the audio just
rides TeleQuick's QUIC media plane, with the phone call routed to you by the
engine (see ``telequick_agents``).

    transport = TeleQuickTransport(call)          # call: telequick_agents.Call
    pipeline = Pipeline([transport.input(), stt, …, tts, transport.output()])

Events: ``on_client_connected`` / ``on_client_disconnected`` fire with the
:class:`telequick_agents.Call` as the client argument.
"""

from __future__ import annotations

from loguru import logger

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    InterruptionFrame,
    OutputAudioRawFrame,
    StartFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.transports.base_input import BaseInputTransport
from pipecat.transports.base_output import BaseOutputTransport
from pipecat.transports.base_transport import BaseTransport, TransportParams

from telequick_agents import Call


class TeleQuickInputTransport(BaseInputTransport):
    """Caller audio (engine → agent) pushed downstream as 20 ms pcm16 frames."""

    def __init__(self, transport: "TeleQuickTransport", call: Call,
                 params: TransportParams, **kwargs):
        super().__init__(params, **kwargs)
        self._transport = transport
        self._call = call
        self._receive_task = None
        self._initialized = False

    async def start(self, frame: StartFrame):
        await super().start(frame)
        if self._initialized:
            return
        self._initialized = True
        await self._transport._on_client_connected()
        if not self._receive_task:
            self._receive_task = self.create_task(self._receive())
        await self.set_transport_ready(frame)

    async def _receive(self):
        try:
            while True:
                pcm = await self._call.recv_audio()
                if pcm is None:
                    break
                await self.push_audio_frame(
                    InputAudioRawFrame(
                        audio=pcm,
                        sample_rate=self._call.sample_rate,
                        num_channels=1,
                    )
                )
        except Exception as e:  # noqa: BLE001
            logger.error(f"{self} exception receiving audio: {e.__class__.__name__} ({e})")
        await self._transport._on_client_disconnected()

    async def _stop_tasks(self):
        if self._receive_task:
            await self.cancel_task(self._receive_task)
            self._receive_task = None

    async def stop(self, frame: EndFrame):
        await super().stop(frame)
        await self._stop_tasks()

    async def cancel(self, frame: CancelFrame):
        await super().cancel(frame)
        await self._stop_tasks()

    async def cleanup(self):
        await super().cleanup()
        await self._stop_tasks()
        await self._transport.cleanup()


class TeleQuickOutputTransport(BaseOutputTransport):
    """Agent audio (agent → engine): paced onto the wire as 20 ms datagrams."""

    def __init__(self, transport: "TeleQuickTransport", call: Call,
                 params: TransportParams, **kwargs):
        super().__init__(params, **kwargs)
        self._transport = transport
        self._call = call
        self._initialized = False

    async def start(self, frame: StartFrame):
        await super().start(frame)
        if self._initialized:
            return
        self._initialized = True
        await self.set_transport_ready(frame)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, InterruptionFrame) and not self._call.ended:
            # Barge-in: drop audio already queued toward the caller so the
            # interrupted speech stops now, not after the buffer drains.
            await self._call.clear()

    async def write_audio_frame(self, frame: OutputAudioRawFrame) -> bool:
        if self._call.ended:
            return False
        await self._call.send_audio(bytes(frame.audio))
        return True

    async def cleanup(self):
        await super().cleanup()
        await self._transport.cleanup()


class TeleQuickTransport(BaseTransport):
    """One Pipecat transport per phone call.

    ``params`` defaults to 8 kHz mono in/out (the PSTN wire rate) with audio
    enabled both ways; pass your own ``TransportParams`` to add VAD etc. —
    but keep the sample rates at ``call.sample_rate``.
    """

    def __init__(self, call: Call, params: TransportParams | None = None,
                 input_name: str | None = None, output_name: str | None = None):
        super().__init__(input_name=input_name, output_name=output_name)
        if params is None:
            params = TransportParams(audio_in_enabled=True, audio_out_enabled=True)
        params.audio_in_sample_rate = params.audio_in_sample_rate or call.sample_rate
        params.audio_out_sample_rate = params.audio_out_sample_rate or call.sample_rate
        self._call = call
        self._params = params
        self._input = TeleQuickInputTransport(self, call, params, name=self._input_name)
        self._output = TeleQuickOutputTransport(self, call, params, name=self._output_name)

        self._register_event_handler("on_client_connected")
        self._register_event_handler("on_client_disconnected")

    @property
    def call(self) -> Call:
        return self._call

    def input(self) -> FrameProcessor:
        return self._input

    def output(self) -> FrameProcessor:
        return self._output

    async def _on_client_connected(self):
        await self._call_event_handler("on_client_connected", self._call)

    async def _on_client_disconnected(self):
        await self._call_event_handler("on_client_disconnected", self._call)
