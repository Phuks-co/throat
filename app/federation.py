""" Here we handle federating with remote servers """
import base64
import json
import logging
import time
import os.path
from pathlib import Path

import requests
import gevent
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from .config import config


class FederationClient:
    def __init__(self):
        self.logger = logging.getLogger("federation")
        self.peers = {}
        self._root = Path(__file__).parent.parent.absolute()
        self.pubkey_file = f"{self._root}/federation.crt"
        self.pubkey = None
        self.privkey_file = f"{self._root}/federation.key"
        self.privkey = None

    def init_app(self, app):
        with app.app_context():
            if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
                return
            if not config.federation.enabled:
                return
            if not os.path.isfile(self.pubkey_file) or not os.path.isfile(
                self.privkey_file
            ):
                self.logger.info("No federation keys found. Generating new ones...")
                self._gen_certs()
            else:
                with open(self.pubkey_file, "rb") as pubkey_file:
                    self.pubkey = serialization.load_pem_public_key(
                        pubkey_file.read(), backend=None
                    )

                with open(self.privkey_file, "rb") as privkey_file:
                    self.privkey = serialization.load_pem_private_key(
                        privkey_file.read(), password=None, backend=None
                    )

            gevent.spawn(self.start, app)

    def start(self, app):
        with app.app_context():
            self.logger.info(
                f"Starting federation. {len(config.federation.peers)} servers to sync."
            )

            for peer in config.federation.peers:
                self.logger.debug(f"Connecting to {peer}")
                self.peers[peer] = {"connected": False, "pubkey": "", "error": None}
                pubkey_dir = f"{self._root}/peers/{peer}.crt"
                if not os.path.isfile(pubkey_dir):
                    self.logger.warning(
                        f"Public key for peer '{peer}' not found in '{pubkey_dir}'. Skipping."
                    )
                    self.peers[peer]["error"] = "Pubkey not found"
                    continue

                with open(pubkey_dir, "rb") as pubkey_file:
                    self.peers[peer]["pubkey"] = serialization.load_pem_public_key(
                        pubkey_file.read(), backend=None
                    )
                ret = self._request(peer, "id")
                self.logger.debug(f" - Response: {ret.text}")
                if ret.json().get("status") == "ok":
                    self.peers[peer]["connected"] = True
                else:
                    self.peers[peer]["error"] = ret.json().get("msg")

    def _request(self, peer, endpoint, data=None):
        if data is None:
            data = {}

        data["timestamp"] = time.time()
        data["peer"] = peer
        data["from"] = config.app.host
        data["endpoint"] = endpoint

        json_data = json.dumps(data)

        signature = self.privkey.sign(
            json_data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )

        headers = {
            "X-Throat-Signature": base64.b64encode(signature),
            "Content-type": "application/json",
        }

        return requests.post(
            f"{config.federation.peers[peer]['address']}/api/f0/{endpoint}",
            data=json_data,
            headers=headers,
        )

    def _gen_certs(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=4096, backend=default_backend()
        )

        self.privkey = private_key

        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        fd = open(self.privkey_file, "w")
        fd.write(pem.decode())
        fd.close()

        public_key = private_key.public_key()
        self.pubkey = public_key

        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        fd = open(self.pubkey_file, "w")
        fd.write(pem.decode())
        fd.close()

    def verify_signature(self, peer, signature, message):
        public_key = self.peers.get(peer, {}).get("pubkey")
        if not public_key:
            return False
        try:
            public_key.verify(
                base64.b64decode(signature),
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        except InvalidSignature:
            return False
        return True


federation = FederationClient()
