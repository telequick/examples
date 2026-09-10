"""Plivo's make-an-outbound-call quickstart, on TeleQuick.

The analog of::

    plivo.RestClient(auth_id, auth_token).calls.create(
        from_='+15550001111', to_='+15552223333',
        answer_url='https://example.com/answer/')

is one management-API operation — ``voice.calls.originate``. Instead of an
answer URL, pass ``agent``: when the callee picks up, the engine routes the
call to that external agent (e.g. the ``greet_caller.py`` worker).

    export TELEQUICK_API_KEY=mpk_...
    export TELEQUICK_ORG=org_...
    python originate_call.py --to +15552223333 --trunk trunk_main --agent plivo-quickstart
"""

import argparse
import os

from telequick_agents.api import TeleQuickAPI


def main() -> None:
    p = argparse.ArgumentParser(description="Originate an outbound call via TeleQuick")
    p.add_argument("--to", required=True, help="destination number, E.164 (e.g. +15552223333)")
    p.add_argument("--from", dest="from_", default=None,
                   help="caller ID / DID to present (defaults to the trunk's DID)")
    p.add_argument("--trunk", required=True, help="trunk id to dial out through")
    p.add_argument("--agent", default=None,
                   help="external agent to connect on answer (the answer_url analog)")
    args = p.parse_args()

    api = TeleQuickAPI(
        base_url=os.environ.get("TELEQUICK_API_URL", "https://app.telequick.dev"),
        api_key=os.environ["TELEQUICK_API_KEY"],
        org_id=os.environ.get("TELEQUICK_ORG"),
    )

    input: dict = {"to": args.to, "trunkId": args.trunk}
    if args.from_:
        input["from"] = args.from_
    if args.agent:
        input["agent"] = args.agent

    result = api.call("voice.calls.originate", input)
    print(f"Originated call sid={result.get('sid')}")
    print(result)


if __name__ == "__main__":
    main()
