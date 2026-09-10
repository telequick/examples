import logging
import os

from flask import Blueprint, jsonify, request
from telequick_agents.webhooks import (
    DELIVERY_HEADER,
    EVENT_HEADER,
    SIGNATURE_HEADER,
    WebhookVerificationError,
    verify_signature,
)

webhook = Blueprint('webhook', __name__)

logger = logging.getLogger(__name__)


@webhook.route('/webhook', methods=['POST'])
def webhook_route():
    # Verify the delivery before trusting anything in the body. The signing
    # secret (whsec_...) is printed once by `python scripts/provision.py webhook`.
    secret = os.environ.get('TELEQUICK_WEBHOOK_SECRET', '')
    try:
        verify_signature(secret, request.headers.get(SIGNATURE_HEADER, ''),
                         request.get_data())
    except WebhookVerificationError as e:
        logger.warning("rejected webhook delivery: %s", e)
        return jsonify({"error": str(e)}), 401

    event = request.headers.get(EVENT_HEADER, '')
    delivery = request.headers.get(DELIVERY_HEADER, '')
    payload = request.get_json(silent=True) or {}
    logger.info("delivery %s: %s", delivery, event)

    if event in ("voice.call.started", "voice.call.answered",
                 "voice.call.ended", "voice.call.failed",
                 "voice.call.transferred"):
        response = status_update_handler(event, payload)
        return jsonify(response), 201
    elif event == "voice.cdr.created":
        response = end_of_call_report_handler(payload)
        return jsonify(response), 201
    elif event == "voice.transcript.ready":
        response = transcript_handler(payload)
        return jsonify(response), 201
    elif event == "voice.recording.ready":
        response = recording_handler(payload)
        return jsonify(response), 201
    else:
        # Subscribed with the 'voice.*' glob? New event types show up here.
        logger.info("unhandled event type %s: %s", event, payload)
        return jsonify({}), 201


def status_update_handler(event, payload):
    """
    Handle Business logic here.
    Sent whenever the status of the call has changed
    (started / answered / ended / failed / transferred) — the analog of Vapi's
    "status-update" server messages.
    You can also store the information in your database, for example whenever
    the call gets transferred.
    """
    logger.info("%s sid=%s to=%s from=%s", event,
                payload.get('sid'), payload.get('to'), payload.get('from'))
    return {}


def end_of_call_report_handler(payload):
    """
    Handle Business logic here.
    voice.cdr.created is the CDR half of Vapi's "end-of-call-report": duration,
    disposition, parties. Store it in your database alongside the transcript
    that arrives separately as voice.transcript.ready.
    """
    logger.info("cdr: %s", payload)
    return {}


def transcript_handler(payload):
    """
    Handle Business logic here.
    Sent once the transcript for a finished call is available — the transcript
    half of Vapi's "end-of-call-report".
    """
    logger.info("transcript ready: %s", payload)
    return {}


def recording_handler(payload):
    """
    Handle Business logic here.
    Sent once the call recording is available for download.
    """
    logger.info("recording ready: %s", payload)
    return {}
