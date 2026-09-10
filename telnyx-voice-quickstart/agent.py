"""Telnyx's voicemail-python Call Control example, on TeleQuick.

Upstream: https://github.com/team-telnyx/telnyx-code-examples/tree/main/voicemail-python

Telnyx drives the call by webhook ping-pong: ``call.initiated`` → send
``answer`` → ``call.answered`` → send ``speak`` → ``call.speak.ended`` → send
``start_recording`` → caller talks → ``call.hangup``. Every step is a REST
command with a webhook round-trip.

Here the whole flow is this one function. The engine answers when it routes
the call to your agent, the greeting is audio you send, and "recording" is the
caller's frames arriving in-process — no command round-trips, no state machine
keyed by call_control_id. Lifecycle webhooks still exist (see
``webhook_server.py``) but they are observability, not control flow.
"""

import asyncio
import math
import time
from pathlib import Path

from telequick_agents import AgentConfig, Call, run

GREETING_WAV = Path(__file__).with_name("greeting.wav")
SAMPLE_RATE = 8000  # PSTN legs are 8 kHz

GREETING_TEXT = (
    "Hello! You've reached our voicemail system. "
    "Please leave your message after the beep, and we'll get back to you soon."
)


def load_greeting() -> bytes:
    """greeting.wav (8 kHz mono pcm16) if present, else a chime + beep.

    Upstream uses Telnyx's ``speak`` command with GREETING_TEXT — here the
    greeting is any WAV you drop in (generate one with the TTS of your
    choice; see README).
    """
    if GREETING_WAV.exists():
        import wave

        with wave.open(str(GREETING_WAV), "rb") as w:
            if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (SAMPLE_RATE, 1, 2):
                raise SystemExit("greeting.wav must be 8 kHz mono 16-bit PCM (see README)")
            return w.readframes(w.getnframes())
    pcm = bytearray()
    for freq, dur in ((1046.5, 0.3), (1318.5, 0.3), (0.0, 0.4), (1000.0, 0.25)):  # chime … beep
        n = int(dur * SAMPLE_RATE)
        for i in range(n):
            env = min(1.0, i / (0.01 * SAMPLE_RATE)) * min(1.0, (n - i) / (0.1 * SAMPLE_RATE))
            s = int(0.35 * env * 32767 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
            pcm += s.to_bytes(2, "little", signed=True)
    return bytes(pcm)


GREETING = load_greeting()


async def voicemail(call: Call) -> None:
    """Answer → greet → take the message → done. One coroutine per call."""
    print(f"Voicemail call from {call.caller_number} to {call.called_number}")
    started = time.monotonic()

    # Telnyx: client.calls.actions.speak(call_control_id, payload=…)
    await call.send_audio(GREETING)
    await call.flush()
    call.send_transcript("assistant", GREETING_TEXT)
    await asyncio.sleep(len(GREETING) / (2 * SAMPLE_RATE))  # let the beep play out

    # Telnyx: start_recording + wait for call.recording.saved. Here the
    # message is just the caller's frames — count them until hangup. (Enable
    # platform recording on the route for a durable copy; you'll get a
    # voice.recording.ready webhook with the file.)
    message_ms = 0
    async for _pcm in call.audio():  # 20 ms pcm16 @ 8 kHz
        message_ms += 20

    print("Voicemail completed:")
    print(f"  From: {call.caller_number}")
    print(f"  Message length: {message_ms / 1000:.1f}s "
          f"(call {time.monotonic() - started:.1f}s total)")


if __name__ == "__main__":
    run(
        voicemail,
        AgentConfig.from_env(),
        on_ready=lambda: print("✓ connected — registered and awaiting calls"),
        on_disconnected=lambda e: print(f"✗ disconnected ({e}); reconnecting…"),
    )
