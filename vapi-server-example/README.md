# Vapi Server Example on TeleQuick

A drop-in port of [VapiAI/server-side-example-python-flask](https://github.com/VapiAI/server-side-example-python-flask) onto the TeleQuick platform. Same Flask layout, same two custom functions (`getRandomName`, `getCharacterInspiration`) — wired to TeleQuick's unified webhooks and HTTP agent tools instead of Vapi server messages.

## What maps to what

| Vapi concept | TeleQuick equivalent |
| --- | --- |
| Assistant | Voice agent, created in the console UI (there is no key-authenticated create operation today) |
| Server URL + `x-vapi-secret` | Unified webhook endpoint (`webhooks.create`), HMAC-signed deliveries verified with `telequick_agents.webhooks.verify_signature` |
| Custom functions (`function-call` messages) | HTTP agent tools (`admin.upsertAgentTool`, `kind: 'http'`) — the platform POSTs tool arguments straight to your Flask routes |
| `status-update` server messages | `voice.call.started` / `answered` / `ended` / `failed` / `transferred` events |
| `end-of-call-report` | `voice.cdr.created` (CDR) + `voice.transcript.ready` (transcript), plus `voice.recording.ready` |
| `POST /call/phone` API | `voice.calls.originate` via `TeleQuickAPI` (`scripts/provision.py call`) |

## Prerequisites

- Python 3.10 or higher
- A TeleQuick management API key (`mpk_...`) from the console under Settings → API keys
- A voice agent created in the console (note its agent id)
- A public URL for your local server (e.g. ngrok)

## Installation

```bash
cd vapi-server-example
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configuring environment variables

Copy `example.env` to `.env` and fill in:

```bash
TELEQUICK_API_URL=https://app.telequick.dev
TELEQUICK_API_KEY=<your mpk_ key>
TELEQUICK_ORG=<your org id>
TELEQUICK_WEBHOOK_SECRET=<printed by the webhook provision step below>
```

## Running the project

```bash
flask --app ./app/main run --port 8000
```

Expose it publicly (e.g. `ngrok http 8000`), then provision the platform side:

```bash
# 1. Register the webhook endpoint (prints the signing secret ONCE — put it in .env)
python scripts/provision.py webhook --url https://<your-tunnel>/webhook

# 2. Attach both custom functions to your agent as HTTP tools
python scripts/provision.py tools --agent-id <agentId> --base-url https://<your-tunnel>

# 3. Optionally originate a test call to yourself
python scripts/provision.py call --to +15551234567 --trunk-id <trunkId> --agent <agent>
```

Talk to the agent and ask for "a random name" or "character inspiration" — the tool calls land on `POST /functions/get_random_name` and `POST /functions/get_character_inspiration`, and the call lifecycle, CDR, transcript and recording events land on `POST /webhook`.

## Notes

- `/webhook` rejects any delivery whose `X-Clutchcall-Signature` does not verify against `TELEQUICK_WEBHOOK_SECRET`, so keep that variable set.
- The upstream sample answers `getCharacterInspiration` with a llama_index vector store over `data/*.md`; this port ships the same data files but uses a dependency-free keyword retrieval. Swap in your own RAG stack in `app/functions/get_character_inspiration.py` if you want semantic search.
