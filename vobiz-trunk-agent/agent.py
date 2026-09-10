"""Minimal AI-ready worker for a Vobiz DID routed through TeleQuick.

Vobiz has no starter to port — it is a SIP trunk / DID provider. This is the
other half: the trunk lands calls on the TeleQuick engine, and the engine
hands each one to this function. Out of the box it greets with
``greeting.wav`` (if present) and then echoes the caller — the echo loop is
exactly where an AI bridge plugs in (see twilio-speech-assistant/ for a full
OpenAI Realtime example built on the same three calls).
"""

from pathlib import Path

from telequick_agents import AgentConfig, Call, run

GREETING_WAV = Path(__file__).with_name("greeting.wav")
SAMPLE_RATE = 8000  # PSTN legs are 8 kHz


def load_greeting() -> bytes | None:
    """greeting.wav (8 kHz mono pcm16) if present, else None (pure echo)."""
    if not GREETING_WAV.exists():
        return None
    import wave

    with wave.open(str(GREETING_WAV), "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise SystemExit("greeting.wav must be 8 kHz mono 16-bit PCM (see README)")
        return w.readframes(w.getnframes())


GREETING = load_greeting()


async def handle_call(call: Call) -> None:
    # ANI/DNIS come straight off the Vobiz trunk leg.
    print(f"Call on Vobiz DID {call.called_number} from {call.caller_number} "
          f"(trunk={call.trunk_id})")
    call.send_transcript("assistant", f"Answered call from {call.caller_number}")

    if GREETING is not None:
        await call.send_audio(GREETING)
        await call.flush()

    # Echo the caller until hangup — replace this loop with your model/pipeline.
    async for pcm in call.audio():  # 20 ms pcm16 @ 8 kHz
        await call.send_audio(pcm)

    print(f"Call from {call.caller_number} ended")


if __name__ == "__main__":
    run(
        handle_call,
        AgentConfig.from_env(),
        on_ready=lambda: print("✓ connected — registered and awaiting calls"),
        on_disconnected=lambda e: print(f"✗ disconnected ({e}); reconnecting…"),
    )
