#!/usr/bin/env python3
"""Provision the platform side of this example.

    python scripts/provision.py webhook --url https://example.ngrok.app/webhook
    python scripts/provision.py tools   --agent-id <agentId> --base-url https://example.ngrok.app
    python scripts/provision.py call    --to +15551234567 --trunk-id trunk_main --agent <agent>

Reads TELEQUICK_API_URL (default https://app.telequick.dev), TELEQUICK_API_KEY
(an mpk_ management key from the console under Settings -> API keys) and
TELEQUICK_ORG from the environment (a .env file is honoured if present).
"""

import argparse
import json
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telequick_agents.api import TeleQuickAPI

WEBHOOK_EVENTS = [
    "voice.call.started",
    "voice.call.answered",
    "voice.call.ended",
    "voice.call.failed",
    "voice.call.transferred",
    "voice.cdr.created",
    "voice.recording.ready",
    "voice.transcript.ready",
]

# The two custom functions from the Vapi sample, as kind:'http' agent tools.
# The agent's LLM calls them mid-call; the platform POSTs the arguments to
# your Flask routes and speaks the returned "result".
TOOLS = [
    {
        "kind": "http",
        "name": "getRandomName",
        "description": "Fetches a random person's name. Optionally takes a "
                       "gender ('male'/'female') and a two-letter nationality "
                       "code such as US, FR or IN.",
        "silent": False,
        "spec": {
            "method": "POST",
            "path": "/functions/get_random_name",
            "parameters": {
                "type": "object",
                "properties": {
                    "gender": {"type": "string", "enum": ["male", "female"]},
                    "nat": {"type": "string",
                            "description": "Two-letter nationality code."},
                },
            },
        },
    },
    {
        "kind": "http",
        "name": "getCharacterInspiration",
        "description": "Looks up character inspiration from a library of "
                       "fictional characters and activities. Pass what kind "
                       "of character the user is after.",
        "silent": False,
        "spec": {
            "method": "POST",
            "path": "/functions/get_character_inspiration",
            "parameters": {
                "type": "object",
                "properties": {
                    "inspiration": {
                        "type": "string",
                        "description": "What the user wants inspiration about.",
                    },
                },
                "required": ["inspiration"],
            },
        },
    },
]


def make_api():
    api_key = os.environ.get("TELEQUICK_API_KEY")
    org_id = os.environ.get("TELEQUICK_ORG")
    if not api_key or not org_id:
        sys.exit("Set TELEQUICK_API_KEY (mpk_...) and TELEQUICK_ORG in the "
                 "environment (see example.env).")
    return TeleQuickAPI(
        base_url=os.environ.get("TELEQUICK_API_URL", "https://app.telequick.dev"),
        api_key=api_key,
        org_id=org_id,
    )


def cmd_webhook(api, args):
    result = api.call("webhooks.create", {
        "vertical": "voice",
        "url": args.url,
        "eventTypes": ["voice.*"] if args.all_events else WEBHOOK_EVENTS,
        "description": "vapi-server-example webhook",
    })
    print(json.dumps(result, indent=2))
    secret = result.get("secret")
    if secret:
        print(f"\nSecret is shown ONCE. Put it in .env:\n"
              f"TELEQUICK_WEBHOOK_SECRET={secret}")


def cmd_tools(api, args):
    base = args.base_url.rstrip("/")
    for tool in TOOLS:
        tool = {**tool, "spec": {**tool["spec"]}}
        tool["spec"]["url"] = base + tool["spec"].pop("path")
        result = api.call("admin.upsertAgentTool", {
            "agentId": args.agent_id,
            "tool": tool,
        })
        print(f"upserted {tool['name']}: {json.dumps(result)}")


def cmd_call(api, args):
    payload = {"to": args.to, "trunkId": args.trunk_id}
    if getattr(args, "from_"):
        payload["from"] = args.from_
    if args.agent:
        payload["agent"] = args.agent
    result = api.call("voice.calls.originate", payload)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("webhook", help="Create the voice webhook endpoint.")
    p.add_argument("--url", required=True,
                   help="Public URL of this app's /webhook route.")
    p.add_argument("--all-events", action="store_true",
                   help="Subscribe with the voice.* glob instead of an "
                        "explicit event list.")
    p.set_defaults(func=cmd_webhook)

    p = sub.add_parser("tools", help="Attach both HTTP tools to an agent.")
    p.add_argument("--agent-id", required=True,
                   help="Voice agent id (create the agent in the console).")
    p.add_argument("--base-url", required=True,
                   help="Public base URL of this app, e.g. the ngrok URL.")
    p.set_defaults(func=cmd_tools)

    p = sub.add_parser("call", help="Originate a test call.")
    p.add_argument("--to", required=True, help="Destination number (E.164).")
    p.add_argument("--trunk-id", required=True, help="Outbound trunk id.")
    p.add_argument("--from", dest="from_", default=None,
                   help="Caller id (optional).")
    p.add_argument("--agent", default=None,
                   help="Agent to place on the call (optional).")
    p.set_defaults(func=cmd_call)

    args = parser.parse_args()
    args.func(make_api(), args)


if __name__ == "__main__":
    main()
