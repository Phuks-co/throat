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

from flask import Blueprint, jsonify, request, Response
from peewee import fn

from .. import misc
from ..models import Sub
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


@bp.after_request
def fed_sign(response: Response):
    response.headers["X-Throat-Signature"] = federation.sign_payload(
        response.data.decode()
    )
    return response


@bp.route("/id", methods=["POST"])
def id_me():
    return jsonify(status="ok")


@bp.route("/sub", methods=["POST"])
def get_sub():
    sub_name = request.json.get("name")
    if not sub_name:
        return (
            jsonify(
                status="error", msg="name parameter required", error="client_error"
            ),
            400,
        )

    try:
        sub_data = (
            Sub.select().where(fn.Lower(Sub.name) == sub_name.lower()).dicts().get()
        )
    except Sub.DoesNotExist:
        return (
            jsonify(status="error", msg="Sub not found", error="object_not_found"),
            404,
        )

    sub_data["metadata"] = misc.getSubData(sub_data["sid"])
    sub_data["metadata"]["rules"] = list(sub_data["metadata"]["rules"].dicts())
    sub_data["mods"] = misc.getSubMods(sub_data["sid"])
    # To prevent sid clashes during local testing
    if request.json.get("from") == "localhost":
        sub_data["sid"] = "r" + sub_data["sid"][1:]
    return jsonify(**sub_data)
