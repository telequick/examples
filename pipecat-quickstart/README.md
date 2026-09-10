# Pipecat Quickstart → TeleQuick

The official [pipecat-quickstart](https://github.com/pipecat-ai/pipecat-quickstart)
bot, answering **real phone calls** instead of a browser tab. Same pipeline,
same services, same event handlers — the transport is the only swap.

## Diff vs upstream

| Upstream (`bot.py`) | This repo |
| --- | --- |
| `create_transport(runner_args, …)` picks Daily / SmallWebRTC | `TeleQuickTransport(call)` per engine-routed phone call |
| `main()` dev runner serves a browser page | `run_pipecat_worker(run_bot, AgentConfig.from_env())` registers over one outbound QUIC session and waits for calls |
| `on_client_connected` gets a WebRTC client | gets the `telequick_agents.Call` (ANI in `call.caller_number`) |
| everything else | **unchanged** |

## Run it

1. Create an **External agent** in the console (Agents → New → External).
   That mints the media key/secret and the agent handle in one step.
2. `cp env.example .env` and fill in the provider keys + media credentials.
3. `uv sync && uv run bot.py`
4. Route a number to the agent (Numbers → assign), then dial it.

The worker keeps one outbound QUIC/WebTransport session open (no inbound
ports, NAT-friendly), reconnects with backoff, and spins one pipeline per
call. Audio is 8 kHz pcm16 both ways — Pipecat resamples the Cartesia TTS
down to the wire rate automatically because the transport declares it.
