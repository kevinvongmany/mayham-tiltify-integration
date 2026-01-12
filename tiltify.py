import hmac
import hashlib
import json
import os

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# Load your Tiltify webhook secret from env
TILTIFY_WEBHOOK_SECRET = os.getenv("TILTIFY_WEBHOOK_SECRET", "")

app = FastAPI()


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Example HMAC verification.
    Adjust the header name / format to match how you configure the secret in Tiltify.
    """
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
    expected = mac.hexdigest()

    # Many providers send hex digest; adjust if Tiltify uses a different scheme.
    # constant-time compare to avoid timing attacks
    return hmac.compare_digest(expected, signature_header)


@app.post("/tiltify/webhook")
async def tiltify_webhook(
    request: Request,
    x_tiltify_signature: str | None = Header(default=None),
):
    """
    Webhook endpoint that receives POSTs from Tiltify.
    """
    # Read raw body first for signature verification
    raw_body = await request.body()

    # Verify signature if secret is configured
    if not verify_signature(raw_body, x_tiltify_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Example: inspect event type and handle it
    # Tiltify webhook payloads will show the event schema in the dashboard's test payload.[web:18]
    event_type = payload.get("type") or payload.get("event")  # adjust to actual field

    if event_type == "donation_updated":
        data = payload.get("data", {})
        amount = data.get("amount", {})
        value = amount.get("value")
        currency = amount.get("currency")
        donor_name = data.get("donor_name")  # field names depend on your event type
        # TODO: persist or process the donation as needed
        print(f"New donation: {value} {currency} from {donor_name}")

    # IMPORTANT: respond 2xx quickly so Tiltify does not deactivate the webhook.[web:1][web:2]
    return JSONResponse({"status": "ok"}, status_code=200)
