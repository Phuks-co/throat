"""
Federation endpoints.

Response format:
{
    "payload": {
        "from": "phuks.co",
        "data": ...
    },
    "signature": ... <signed data from `payload`>
}
"""

from flask import Blueprint, jsonify, request

from ..config import config
from ..federation import federation

bp = Blueprint("federation", __name__)


@bp.before_request
def fed_authenticate():
    if not request.is_json:
        return (
            jsonify(status="error", msg="JSON payload expected", error="client_error"),
            400,
        )

    signature = request.headers.get("X-Throat-Signature")
    if not signature:
        return (
            jsonify(status="error", msg="Signature not found", error="client_error"),
            400,
        )

    req_from = request.json.get("from")

    if not req_from or req_from not in config.federation.peers.keys():
        return (
            jsonify(
                status="error", msg="Host not allowed to peer", error="not_authorized"
            ),
            403,
        )

    # Verify signature
    if not federation.verify_signature(req_from, signature, request.get_data()):
        return (
            jsonify(status="error", msg="Invalid signature", error="invalid_signature"),
            400,
        )


@bp.route("/id", methods=["POST"])
def id_me():
    return jsonify(status="ok")
