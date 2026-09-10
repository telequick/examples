# TeleQuick provider starters

Drop-in ports of popular voice-provider starter apps onto the TeleQuick SDK.
Each directory clones the structure of the provider's **official** sample and
swaps only the provider SDK — your agent logic, provider AI keys, and app
shape stay recognizable, so migrating means a diff, not a rewrite.

| Starter | Upstream it ports | The swap |
| --- | --- | --- |
| [`pipecat-quickstart/`](pipecat-quickstart/) | pipecat-ai/pipecat-quickstart | `create_transport(...)` → `TeleQuickTransport(call)`; browser tab → phone call |
| [`twilio-speech-assistant/`](twilio-speech-assistant/) | twilio-samples/speech-assistant-openai-realtime-api-python | TwiML + Media Streams WS → external-agent `Call` (same OpenAI Realtime bridge) |
| [`vapi-server-example/`](vapi-server-example/) | VapiAI/server-side-example-python-flask | Vapi server webhooks + custom functions → unified webhooks + HTTP agent tools |
| [`plivo-voice-quickstart/`](plivo-voice-quickstart/) | plivo/plivo-examples-python (voice) | XML answer-URL (`<Speak>`) → agent audio; REST originate → `voice.calls.originate` |
| [`telnyx-voice-quickstart/`](telnyx-voice-quickstart/) | team-telnyx/telnyx-code-examples | Call Control webhook commands → in-process audio + lifecycle webhooks |
| [`vobiz-trunk-agent/`](vobiz-trunk-agent/) | — (SIP trunk provider; no code starter) | bring your Vobiz trunk/DID, route to any agent |

A LiveKit Agents port also exists — `livekit-plugins-clutchcall` /
`@clutchcall/livekit-transport` — in its own repo, same seam.

## The seam

All starters use two packages from `packages/` (published to
`https://artifacts.clutchcall.dev/pip/simple/`):

- **`telequick-agents`** — external-agent SDK. Your process dials ONE outbound
  QUIC/WebTransport session, authenticates with a media app key/secret, and
  handles each routed call: `call.audio()` (20 ms pcm16 @ 8 kHz),
  `send_audio`, `clear` (barge-in), `send_transcript`, ANI/DNIS/trunk, and the
  agent's resource `tags`. Plus `TeleQuickAPI` (management ops with an `mpk_`
  key) and webhook signature verification. One SDK, one directory per
  language under `packages/telequick-agents/`: `python/` (pip
  `telequick-agents`), `typescript/` (npm `@telequick/agents`), `go/`
  (`github.com/telequick/agents`), `rust/` (crate `telequick-agents`) — same
  wire protocol, same `serve(handler)` shape, each with an `examples/echo`.
- **`pipecat-telequick`** — Pipecat `BaseTransport` on top of it.

Provisioning is one console flow: Agents → **External agent** mints the media
credential and handle; route a number to the agent; run the starter.

## Tests

- `packages/telequick-agents/python`: `python3 -m unittest discover -s tests` (no deps)
- `packages/telequick-agents/typescript`: `npm run typecheck` (tsc strict)
- `packages/telequick-agents/go`: `go vet ./... && go test ./...`
- `packages/telequick-agents/rust`: `cargo test` (unit + doctest)
- `packages/pipecat-telequick`: `docker build -f tests/Dockerfile …` runs a
  full Pipeline smoke against real `pipecat-ai`.
