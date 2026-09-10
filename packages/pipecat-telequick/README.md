# pipecat-telequick

TeleQuick transport for [Pipecat](https://github.com/pipecat-ai/pipecat): run
an unmodified Pipecat pipeline on real phone calls. Drop-in for the Daily /
SmallWebRTC / websocket transports — your services, aggregators, and event
handlers stay as written.

```python
from pipecat_telequick import TeleQuickTransport, run_pipecat_worker
from telequick_agents import AgentConfig

async def run_bot(transport, call):
    pipeline = Pipeline([transport.input(), stt, llm, tts, transport.output()])
    ...  # your existing bot, verbatim

asyncio.run(run_pipecat_worker(run_bot, AgentConfig.from_env()))
```

- One outbound QUIC session; one pipeline per engine-routed call.
- `on_client_connected` / `on_client_disconnected` fire with the
  `telequick_agents.Call` (caller number, transcripts, barge-in).
- The transport declares the 8 kHz wire rate, so Pipecat resamples TTS
  automatically; pipeline `InterruptionFrame`s clear the caller-side buffer.

Install: `pip install pipecat-telequick --extra-index-url
https://artifacts.clutchcall.dev/pip/simple/`
