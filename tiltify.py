import hmac
import base64
import hashlib
import json
import os
from typing import Annotated
import websockets
import asyncio
from random import choice

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# Load your Tiltify webhook secret from env
TILTIFY_WEBHOOK_SECRET = os.getenv("TILTIFY_WEBHOOK_SECRET", "")

app = FastAPI()


async def send_ws_message(message):
    uri = "wss://l0axmgjep7.execute-api.ap-southeast-2.amazonaws.com/beta"

    message = {
        "action": "sendmessage",
        "message": message
    }

    async with websockets.connect(uri) as websocket:
        # Send the message as a JSON string
        await websocket.send(json.dumps(message))
        print(f"Sent: {message}")

        # Optionally receive a reply
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=3)
            print("Received:", response)
        except asyncio.TimeoutError:
            print("No reply received (timeout or no server response)")

async def invoke_override(tier: str) -> None:
    override_tiers = {
        "tier_1": [
            "pull_ghost",
            "open_inventory",
            "jump_and_ability",
            "class_ability",
            "powered_melee",
            "look_down",
            "turn_around",
        ],
        "tier_2": [
            "throw_grenade",
            "super",
            "transcendence",
            "jumpscare",
            "hold_forward",
        ],
        "tier_3": [
            "all_abilities",
            "dump_heavy",
            "dump_kinetic",
            "random_loadout",
            "dance_party",
        ],
        "tier_4": ["alt_f4"]
    }
    print(f"Invoking a {tier} command")
    selected_override = override_tiers[tier]
    random_command = choice(selected_override)
    print(f"Command triggered: {random_command}")
    await send_ws_message(random_command)

def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    if not TILTIFY_WEBHOOK_SECRET:
        # If you have not configured a secret, skip verification (not recommended)
        return True

    if not signature_header:
        return False

    # Compute HMAC-SHA256 of the raw body using your secret
    mac = hmac.new(
        TILTIFY_WEBHOOK_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    )
    digest_bytes = mac.digest()
    expected = base64.b64encode(digest_bytes).decode("utf-8")

    # Many providers send hex digest; adjust if Tiltify uses a different scheme.
    # constant-time compare to avoid timing attacks
    return hmac.compare_digest(expected, signature_header)


@app.post("/tiltify/webhook")
async def tiltify_webhook(
    request: Request,
    x_tiltify_signature: Annotated[str | None, Header()] = None,
    x_tiltify_timestamp: Annotated[str | None, Header()] = None,
):
    """
    Webhook endpoint that receives POSTs from Tiltify.
    """
    raw_body = await request.body()

    signed_payload = f"{x_tiltify_timestamp}.{raw_body.decode("utf-8")}".encode("utf-8")

    if not verify_signature(signed_payload, x_tiltify_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    meta_data = payload.get("meta", {})
    event_type = meta_data.get("event_type")

    if "donation_updated" in event_type:
        data = payload.get("data", {})
        amount = data.get("amount", {})
        raw_value = amount.get("value")
        value = float(raw_value)
        currency = amount.get("currency")
        donor_name = payload.get("donor_name") 
        if currency == "USD":
            if value >= 7 and value < 14:
                await invoke_override("tier_1")
            elif value >= 14 and value < 70:
                await invoke_override("tier_2")
            elif value >= 70 and value < 250:
                await invoke_override("tier_3")
            elif value >= 250:
                await invoke_override("tier_4")
        print(f"New donation: {value} {currency} from {donor_name}")

    # IMPORTANT: respond 2xx quickly so Tiltify does not deactivate the webhook.[web:1][web:2]
    return JSONResponse({"status": "ok"}, status_code=200)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
