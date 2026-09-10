"""HTTP tool endpoints — the analog of Vapi custom functions.

Each route is attached to a voice agent as a kind:'http' tool (see
scripts/provision.py). Mid-call, when the agent's LLM decides to call the
tool, the platform POSTs the tool arguments here as JSON and speaks the
returned "result".
"""

from flask import Blueprint, jsonify, request

from app.functions import get_character_inspiration, get_random_name

function_call = Blueprint('function_call', __name__)


def _arguments():
    body = request.get_json(silent=True) or {}
    # Accept both a flat argument object and an {"arguments": {...}} envelope.
    args = body.get('arguments', body)
    return args if isinstance(args, dict) else {}


@function_call.route('/get_random_name', methods=['POST'])
def get_random_name_route():
    args = _arguments()
    params = get_random_name.NameParams(gender=args.get('gender'),
                                        nat=args.get('nat'))
    return jsonify(get_random_name.get_random_name(params)), 201


@function_call.route('/get_character_inspiration', methods=['POST'])
def get_character_inspiration_route():
    args = _arguments()
    return jsonify(get_character_inspiration.get_character_inspiration(
        inspiration=args.get('inspiration'))), 201
