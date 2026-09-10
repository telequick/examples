"""End-to-end smoke against REAL pipecat: a full Pipeline run.

Caller audio is injected as engine datagrams; the pipeline echoes audio out
through the transport (via a passthrough processor); we assert paced 20 ms
datagrams leave the wire, the connected/disconnected events fire, and the
pipeline shuts down cleanly on call end.
"""

import asyncio

from pipecat.frames.frames import Frame, InputAudioRawFrame, OutputAudioRawFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from pipecat_telequick import TeleQuickTransport
from telequick_agents import wire
from telequick_agents.agent import Call
from telequick_agents.transport import WebTransportConfig, WebTransportSession
from telequick_agents.types import JobAssign


class EchoProcessor(FrameProcessor):
    """Turn caller audio into bot audio (stands in for STT→LLM→TTS)."""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            await self.push_frame(
                OutputAudioRawFrame(
                    audio=frame.audio,
                    sample_rate=frame.sample_rate,
                    num_channels=frame.num_channels,
                )
            )
        else:
            await self.push_frame(frame, direction)


async def main() -> None:
    cfg = WebTransportConfig(
        engine_url="https://engine.example.com", app_key="k", app_secret="s",
        agent_name="salesbot", call_id=1, sample_rate=8000,
    )
    dgs, ctrl = [], []
    sess = WebTransportSession(cfg, send_datagram=dgs.append, send_stream=ctrl.append)
    call = Call(JobAssign(call_id=1, caller_number="+15550001111"), sess)

    transport = TeleQuickTransport(call)
    events = []

    @transport.event_handler("on_client_connected")
    async def _on_conn(t, c):
        events.append(("connected", c.caller_number))

    @transport.event_handler("on_client_disconnected")
    async def _on_disc(t, c):
        events.append(("disconnected", c.caller_number))

    task = PipelineTask(
        Pipeline([transport.input(), EchoProcessor(), transport.output()]),
        params=PipelineParams(audio_in_sample_rate=8000, audio_out_sample_rate=8000),
    )

    async def drive():
        # ~0.5 s of caller audio, 20 ms frames, then hangup.
        await asyncio.sleep(0.5)
        for seq in range(25):
            sess.on_datagram(
                wire.encode_datagram(
                    wire.Datagram(call_id=1, seq=seq, payload=bytes(320))
                )
            )
            await asyncio.sleep(0.02)
        await asyncio.sleep(1.0)
        sess.on_control({"op": "shutdown", "call_id": 1})
        await asyncio.sleep(0.3)
        await task.cancel()

    driver = asyncio.create_task(drive())
    await PipelineRunner(handle_sigint=False).run(task)
    await driver

    assert ("connected", "+15550001111") in events, events
    assert ("disconnected", "+15550001111") in events, events
    assert len(dgs) >= 10, f"expected paced egress datagrams, got {len(dgs)}"
    payload = wire.decode_datagram(dgs[0]).payload
    assert len(payload) == 320, len(payload)
    print(f"SMOKE OK — events={events} egress_datagrams={len(dgs)}")


if __name__ == "__main__":
    asyncio.run(main())
