# Bring your Vobiz DID to TeleQuick

Vobiz is an Indian SIP-trunk / DID provider — there is no "Vobiz starter app"
to port, because the app half is exactly what TeleQuick provides. This starter
connects the two: your Vobiz trunk delivers calls to the TeleQuick engine, the
engine routes the DID to an external agent, and `agent.py` (your Python
process, running anywhere) gets the live audio.

```
caller → PSTN → Vobiz trunk → TeleQuick engine → agent.py (your process)
```

This is the exact architecture serving production Indian DIDs today — a Vobiz
trunk into the TeleQuick engine with external agents on the far end. Nothing
here is a mock-up.

## 1. Add your Vobiz trunk

Console → Voice → **Trunks** → Add trunk. Two auth styles; use whichever your
Vobiz account is set up for:

- **Registration**: enter the SIP domain/registrar, username, and password
  from your Vobiz trunk credentials. The engine registers outbound; nothing
  needs to reach your network.
- **IP auth (static)**: point the trunk at the engine's signaling IP shown in
  the console, and add that IP to your Vobiz account's allowed/dispatch list.
  Vobiz sends INVITEs for your DID straight to the engine.

Enter your own credentials — none are shipped here.

## 2. Route the DID to an external agent

1. Console → Agents → **External agent** → create one (e.g. handle
   `vobiz-agent`). This mints the media key/secret in the same step.
2. Console → Voice → Numbers → your Vobiz DID → route to that agent.

## 3. Run the agent

```bash
cp env.example .env       # fill in TELEQUICK_* from step 2, then export
pip install -r requirements.txt
python agent.py
```

Dial the DID. The worker logs the caller/called numbers (ANI/DNIS straight
off the trunk leg), plays `greeting.wav` if you dropped one in (any 8 kHz mono
16-bit WAV — e.g. OpenAI TTS piped through
`ffmpeg -i tts.wav -ar 8000 -ac 1 -sample_fmt s16 greeting.wav`), then echoes
your voice back and forwards a transcript line into platform analytics.

## Make it an AI agent

The echo loop in `handle_call` is the seam:

```python
async for pcm in call.audio():        # caller → your model
    await call.send_audio(pcm)        # your model → caller
```

Swap it for a bridge to any realtime model — `twilio-speech-assistant/` in
this repo is the full OpenAI Realtime version, and it runs unchanged on a
Vobiz-delivered call: the worker never knows or cares which trunk the call
came in on. `call.clear()` gives you barge-in; `call.send_transcript()` lands
turns in platform transcripts and fires `voice.transcript.ready` webhooks.

Note: the worker dials **out** to the engine over QUIC — no public IP, no port
forwarding, no ngrok. It can run on a laptop behind NAT while the trunk and
DID stay in production.
