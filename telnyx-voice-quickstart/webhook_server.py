"""Lifecycle webhook receiver — the observability half of the Telnyx port.

Telnyx's example *needs* its webhook route to run the call. Here calls run in
``agent.py``; this server just receives the platform's ``voice.*`` lifecycle
events (started / answered / ended / recording ready / transcript ready…),
verifies the ``X-Clutchcall-Signature`` header, and prints them.

Stdlib only — no Flask — so it runs anywhere:

    export TELEQUICK_WEBHOOK_SECRET=whsec_...   # printed by provision_webhook.py
    python webhook_server.py                    # listens on :8000 (PORT to change)
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from telequick_agents.webhooks import (
    DELIVERY_HEADER,
    EVENT_HEADER,
    SIGNATURE_HEADER,
    WebhookVerificationError,
    verify_signature,
)

SECRET = os.environ.get("TELEQUICK_WEBHOOK_SECRET", "")
PORT = int(os.environ.get("PORT", "8000"))


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 — http.server API
        body = self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))

        if SECRET:
            try:
                verify_signature(SECRET, self.headers.get(SIGNATURE_HEADER, ""), body)
            except WebhookVerificationError as e:
                print(f"REJECTED delivery: {e}")
                self.send_response(400)
                self.end_headers()
                return
        else:
            print("WARNING: TELEQUICK_WEBHOOK_SECRET not set — skipping verification")

        event = self.headers.get(EVENT_HEADER, "?")
        delivery = self.headers.get(DELIVERY_HEADER, "?")
        try:
            payload = json.loads(body) if body else {}
        except ValueError:
            payload = {"raw": body.decode(errors="replace")}
        print(f"[{event}] delivery={delivery}")
        print(json.dumps(payload, indent=2))

        self.send_response(204)
        self.end_headers()

    def log_message(self, *args) -> None:  # quiet the default access log
        pass


if __name__ == "__main__":
    print(f"Listening for voice.* webhooks on :{PORT} "
          f"(verification {'ON' if SECRET else 'OFF'})")
    HTTPServer(("", PORT), WebhookHandler).serve_forever()
