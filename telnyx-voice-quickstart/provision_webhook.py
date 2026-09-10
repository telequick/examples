"""Register a webhook endpoint for voice lifecycle events.

The analog of pointing your Telnyx Call Control Application's webhook URL at
your server — except it is one management-API call, and the events are
observability rather than the thing that drives the call.

    export TELEQUICK_API_KEY=mpk_...
    export TELEQUICK_ORG=org_...
    python provision_webhook.py --url https://example.com/webhooks/voice

Prints the endpoint's signing secret (whsec_…) ONCE — export it as
TELEQUICK_WEBHOOK_SECRET for webhook_server.py.
"""

import argparse
import os

from telequick_agents.api import TeleQuickAPI

DEFAULT_EVENTS = [
    "voice.call.started",
    "voice.call.answered",
    "voice.call.ended",
    "voice.call.failed",
    "voice.call.transferred",
    "voice.cdr.created",
    "voice.recording.ready",
    "voice.transcript.ready",
]


def main() -> None:
    p = argparse.ArgumentParser(description="Create a TeleQuick voice webhook endpoint")
    p.add_argument("--url", required=True, help="public HTTPS URL deliveries are POSTed to")
    p.add_argument("--events", default=",".join(DEFAULT_EVENTS),
                   help="comma-separated event types (default: all voice events)")
    args = p.parse_args()

    api = TeleQuickAPI(
        base_url=os.environ.get("TELEQUICK_API_URL", "https://app.telequick.dev"),
        api_key=os.environ["TELEQUICK_API_KEY"],
        org_id=os.environ.get("TELEQUICK_ORG"),
    )

    result = api.call("webhooks.create", {
        "vertical": "voice",
        "url": args.url,
        "eventTypes": [e.strip() for e in args.events.split(",") if e.strip()],
    })
    print("Webhook endpoint created:")
    print(result)
    print("\nSave the whsec_ signing secret above — it is shown only once. "
          "Export it as TELEQUICK_WEBHOOK_SECRET for webhook_server.py.")


if __name__ == "__main__":
    main()
