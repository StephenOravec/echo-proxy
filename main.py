import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "https://oravec.io")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("echo-proxy")

# App Setup
app = Flask(__name__)
CORS(app, origins=[FRONTEND_ORIGIN])

def get_id_token_for_backend(audience: str) -> str:
    """Get Google ID token for backend authentication."""
    req = GoogleRequest()
    return google_id_token.fetch_id_token(req, audience)

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "echo-proxy-running"}), 200

@app.route("/chat", methods=["POST"])
def chat_proxy():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    # Forward the payload as-is to echo-bot
    if not BACKEND_URL:
        logger.error("BACKEND_URL is not configured")
        return jsonify({"error": "Server misconfiguration"}), 500

    try:
        id_token = get_id_token_for_backend(BACKEND_URL)
    except Exception as e:
        logger.exception("Failed to get ID token: %s", e)
        return jsonify({"error": "Failed to authenticate to backend"}), 500

    try:
        resp = requests.post(
            BACKEND_URL,
            json=data,
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json"
            },
            timeout=15
        )
        return resp.json(), resp.status_code
    except requests.RequestException as e:
        logger.exception("Backend request failed: %s", e)
        return jsonify({"error": "Failed to reach backend"}), 502
    except ValueError:
        return resp.text, resp.status_code
