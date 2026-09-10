"""Twilio's speech-assistant-openai-realtime-api-python, on TeleQuick.

Upstream: https://github.com/twilio-samples/speech-assistant-openai-realtime-api-python

The OpenAI Realtime bridge — session setup, μ-law audio both ways, barge-in
with ``conversation.item.truncate`` — is the upstream file's, near-verbatim.
What Twilio did with TwiML + a Media Streams WebSocket, TeleQuick does with an
engine-routed call handed to this worker:

    Twilio                                  TeleQuick
    ------                                  ---------
    /incoming-call webhook returns TwiML    number routed to your external agent
    <Connect><Stream url=wss://…/>          engine dispatches a Call to this worker
    WS "media" events (base64 μ-law)        call.audio() frames (pcm16 → g711)
    WS {"event":"clear"}                    call.clear()
    mark queue for playback tracking        response-item timing (below)
"""

import asyncio
import base64
import json
import os

import websockets
from dotenv import load_dotenv

from telequick_agents import AgentConfig, Call, run
from telequick_agents.g711 import pcm_to_ulaw, ulaw_to_pcm

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.8))
SYSTEM_MESSAGE = (
    "You are a helpful and bubbly AI assistant who loves to chat about "
    "anything the user is interested in and is prepared to offer them facts. "
    "You have a penchant for dad jokes, owl jokes, and rickrolling – subtly. "
    "Always stay positive, but work in a joke when appropriate."
)
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created', 'session.updated'
]
SHOW_TIMING_MATH = False

if not OPENAI_API_KEY:
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')


async def handle_call(call: Call):
    """Bridge one phone call to the OpenAI Realtime API."""
    print(f"Call from {call.caller_number} to {call.called_number}")

    async with websockets.connect(
        f"wss://api.openai.com/v1/realtime?model=gpt-realtime&temperature={TEMPERATURE}",
        additional_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
    ) as openai_ws:
        await initialize_session(openai_ws)

        # Connection specific state
        latest_media_timestamp = 0
        last_assistant_item = None
        response_start_timestamp = None

        async def receive_from_caller():
            """Receive caller audio from TeleQuick and send it to OpenAI."""
            nonlocal latest_media_timestamp
            async for pcm in call.audio():  # 20 ms pcm16 @ 8 kHz
                latest_media_timestamp += 20
                if openai_ws.state.name == 'OPEN':
                    audio_append = {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(pcm_to_ulaw(pcm)).decode('utf-8')
                    }
                    await openai_ws.send(json.dumps(audio_append))
            print("Caller hung up.")
            if openai_ws.state.name == 'OPEN':
                await openai_ws.close()

        async def send_to_caller():
            """Receive events from OpenAI, send audio back to the caller."""
            nonlocal last_assistant_item, response_start_timestamp
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    if response['type'] in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)

                    if response.get('type') == 'response.output_audio.delta' and 'delta' in response:
                        await call.send_audio(ulaw_to_pcm(base64.b64decode(response['delta'])))

                        if response.get("item_id") and response["item_id"] != last_assistant_item:
                            response_start_timestamp = latest_media_timestamp
                            last_assistant_item = response["item_id"]
                            if SHOW_TIMING_MATH:
                                print(f"Setting start timestamp for new response: {response_start_timestamp}ms")

                    # Optional platform parity: finalized turns land in TeleQuick
                    # transcript storage + voice.transcript.ready webhooks.
                    if response.get('type') == 'response.output_audio_transcript.done':
                        call.send_transcript("assistant", response.get('transcript', ''))
                    if response.get('type') == 'conversation.item.input_audio_transcription.completed':
                        call.send_transcript("user", response.get('transcript', ''))

                    # Trigger an interruption on caller speech, like upstream.
                    if response.get('type') == 'input_audio_buffer.speech_started':
                        print("Speech started detected.")
                        if last_assistant_item:
                            print(f"Interrupting response with id: {last_assistant_item}")
                            await handle_speech_started_event()
            except Exception as e:
                print(f"Error in send_to_caller: {e}")

        async def handle_speech_started_event():
            """Handle interruption when the caller's speech starts."""
            nonlocal response_start_timestamp, last_assistant_item
            print("Handling speech started event.")
            if last_assistant_item and response_start_timestamp is not None:
                elapsed_time = latest_media_timestamp - response_start_timestamp
                if SHOW_TIMING_MATH:
                    print(f"Calculating elapsed time for truncation: {latest_media_timestamp} - {response_start_timestamp} = {elapsed_time}ms")

                truncate_event = {
                    "type": "conversation.item.truncate",
                    "item_id": last_assistant_item,
                    "content_index": 0,
                    "audio_end_ms": elapsed_time
                }
                await openai_ws.send(json.dumps(truncate_event))

                # Twilio: {"event":"clear","streamSid":…} — TeleQuick:
                await call.clear()

                last_assistant_item = None
                response_start_timestamp = None

        await asyncio.gather(receive_from_caller(), send_to_caller())


async def send_initial_conversation_item(openai_ws):
    """Send initial conversation item if AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Greet the user with 'Hello there! I am an AI voice assistant powered by TeleQuick and the OpenAI Realtime API. You can ask me for facts, jokes, or anything you can imagine. How can I help you?'"
                }
            ]
        }
    }
    await openai_ws.send(json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps({"type": "response.create"}))


async def initialize_session(openai_ws):
    """Control initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "model": "gpt-realtime",
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcmu"},
                    "turn_detection": {"type": "server_vad"}
                },
                "output": {
                    "format": {"type": "audio/pcmu"},
                    "voice": VOICE
                }
            },
            "instructions": SYSTEM_MESSAGE,
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

    # Phone callers expect the agent to speak first.
    await send_initial_conversation_item(openai_ws)


if __name__ == "__main__":
    run(
        handle_call,
        AgentConfig.from_env(),
        on_ready=lambda: print("✓ connected — registered and awaiting calls"),
        on_disconnected=lambda e: print(f"✗ disconnected ({e}); reconnecting…"),
    )
