# Telnyx Voice Quickstart (Call Control voicemail) → TeleQuick

A port of Telnyx's
[voicemail-python](https://github.com/team-telnyx/telnyx-code-examples/tree/main/voicemail-python)
Call Control example: answer an inbound call, speak a greeting, take the
caller's message, log it on hangup.

Telnyx's model is webhook-driven command ping-pong — every event
(`call.initiated`, `call.answered`, `call.speak.ended`, …) hits your Flask
route, which issues the next REST command and tracks a per-call state machine
keyed by `call_control_id`. On TeleQuick the audio is **in your process**: the
engine routes the call to your worker, and the whole voicemail flow is one
coroutine (`agent.py`) with zero command round-trips. Webhooks still exist —
as unified lifecycle notifications, not control flow.

## Command → TeleQuick mapping

| Telnyx Call Control | TeleQuick |
| --- | --- |
| `client.calls.actions.answer(ccid)` on `call.initiated` | automatic when the engine routes the call to your agent |
| `client.calls.actions.speak(ccid, payload=…)` | `await call.send_audio(pcm16)` + `await call.flush()` |
| `client.calls.actions.start_recording(ccid)` | caller frames arrive directly via `call.audio()`; enable platform recording on the route for a durable file (`voice.recording.ready` webhook) |
| `client.calls.actions.hangup(ccid)` | return from the handler; for other calls: `voice.calls.hangup {orgId, sid}` |
| `call_sessions[ccid]` state machine | local variables in one coroutine per call |
| Call Control webhook URL (drives the call) | unified `voice.*` webhooks (observability): `webhook_server.py` + `provision_webhook.py` |
| webhook signature (`telnyx-signature-ed25519`) | `X-Clutchcall-Signature` + `telequick_agents.webhooks.verify_signature` |
| `from` / `to` in webhook payload | `call.caller_number` / `call.called_number` |

## Files

- `agent.py` — the voicemail worker (greeting → beep → take the message).
- `webhook_server.py` — stdlib-only receiver that verifies and prints
  `voice.*` lifecycle events.
- `provision_webhook.py` — registers your endpoint via `webhooks.create`.

## Run it

1. Console → Agents → **External agent** → mint a media key/secret and a
   handle (e.g. `telnyx-voicemail`), and route a number to it.
2. `cp env.example .env`, fill in the values, and export them.
3. `pip install -r requirements.txt`
4. `python agent.py` — dial the routed number and leave a message.

The default greeting is a synthesized chime + beep. For a spoken greeting drop
in any 8 kHz mono 16-bit `greeting.wav` (e.g. OpenAI TTS then
`ffmpeg -i tts.wav -ar 8000 -ac 1 -sample_fmt s16 greeting.wav`).

### Lifecycle webhooks (optional)

```bash
export TELEQUICK_API_KEY=mpk_... TELEQUICK_ORG=org_...
python provision_webhook.py --url https://your-host.example.com/webhooks/voice
export TELEQUICK_WEBHOOK_SECRET=whsec_...   # printed once by the step above
python webhook_server.py
```

Note the inversion from Telnyx: their webhook endpoint must be public because
it *is* the app. Here `agent.py` dials out to the engine (no public URL, no
ngrok), and only the optional webhook receiver needs to be reachable.
