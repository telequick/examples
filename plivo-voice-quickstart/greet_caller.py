"""Plivo's greet-the-caller quickstart (voice/greet_caller.py +
voice/receive_calls.py), on TeleQuick.

Upstream, Plivo answers an inbound call by fetching your *answer URL* and
executing the XML it returns — ``<Response><Speak>Hello…</Speak></Response>``.
There is no answer URL here: route the number to this external agent in the
console and the engine hands the live call straight to ``greet_caller`` below.
The ``<Speak>`` becomes audio *you* send — any 8 kHz mono pcm16 WAV dropped in
as ``greeting.wav`` (use the TTS of your choice; see README), with a
synthesized two-tone chime as the batteries-included fallback.
"""

import asyncio
import math
from pathlib import Path

from telequick_agents import AgentConfig, Call, run

GREETING_WAV = Path(__file__).with_name("greeting.wav")
SAMPLE_RATE = 8000  # PSTN legs are 8 kHz


def load_greeting() -> bytes:
    """greeting.wav (8 kHz mono pcm16) if present, else a two-tone chime."""
    if GREETING_WAV.exists():
        import wave

        with wave.open(str(GREETING_WAV), "rb") as w:
            if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (SAMPLE_RATE, 1, 2):
                raise SystemExit("greeting.wav must be 8 kHz mono 16-bit PCM (see README)")
            return w.readframes(w.getnframes())
    # No WAV yet — synthesize a short pleasant chime (C6 then E6) instead.
    pcm = bytearray()
    for freq in (1046.5, 1318.5):
        n = int(0.35 * SAMPLE_RATE)
        for i in range(n):
            env = min(1.0, i / (0.01 * SAMPLE_RATE)) * min(1.0, (n - i) / (0.12 * SAMPLE_RATE))
            s = int(0.35 * env * 32767 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
            pcm += s.to_bytes(2, "little", signed=True)
    return bytes(pcm)


GREETING = load_greeting()


async def greet_caller(call: Call) -> None:
    """Answer, play the greeting, hang up — Plivo's <Speak> flow."""
    print(f"Incoming call from {call.caller_number} to {call.called_number}")
    await call.send_audio(GREETING)  # one shot; the SDK paces it onto the wire
    await call.flush()
    call.send_transcript("assistant", "Hello, welcome to TeleQuick.")
    # Wait for the greeting to actually play out, plus a beat, then hang up
    # (returning from the handler ends the call — Plivo's implicit end-of-XML).
    await asyncio.sleep(len(GREETING) / (2 * SAMPLE_RATE) + 1.0)


if __name__ == "__main__":
    run(
        greet_caller,
        AgentConfig.from_env(),
        on_ready=lambda: print("✓ connected — registered and awaiting calls"),
        on_disconnected=lambda e: print(f"✗ disconnected ({e}); reconnecting…"),
    )
