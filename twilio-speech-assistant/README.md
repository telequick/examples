# Twilio Speech Assistant (OpenAI Realtime) → TeleQuick

A port of Twilio's official sample
[speech-assistant-openai-realtime-api-python](https://github.com/twilio-samples/speech-assistant-openai-realtime-api-python):
a phone caller talks to the OpenAI Realtime API. The OpenAI bridge —
μ-law audio both ways, server VAD, barge-in via `conversation.item.truncate` —
is upstream's code. Everything Twilio-specific is replaced by the TeleQuick
external-agent SDK.

## What maps to what

| Twilio sample | This port |
| --- | --- |
| `POST /incoming-call` returns TwiML `<Connect><Stream>` | none — route the number to your external agent in the console |
| FastAPI `/media-stream` WebSocket | `run(handle_call, AgentConfig.from_env())` worker (outbound QUIC, no public endpoint, no ngrok) |
| `{"event":"media","media":{"payload":base64 μ-law}}` | `call.audio()` pcm16 frames + `g711.pcm_to_ulaw` (OpenAI still speaks `audio/pcmu`) |
| `{"event":"clear"}` on barge-in | `await call.clear()` |
| `mark` queue to track playback | response-item timing (`latest_media_timestamp`) |
| caller number in webhook params | `call.caller_number` / `call.called_number` |

Bonus over upstream: finalized turns are forwarded with
`call.send_transcript(...)`, so transcripts land in platform storage and fire
`voice.transcript.ready` webhooks like a native agent's.

## Run it

1. Console → Agents → **External agent** → mint media key/secret + handle.
2. `cp env.example .env`, fill `OPENAI_API_KEY` + `TELEQUICK_*`.
3. `pip install -r requirements.txt && python main.py`
4. Route a number to the agent and dial it.

Note: no public URL is needed. Twilio's sample requires ngrok because Twilio
must reach *your* server; here your worker dials **out** to the engine.
