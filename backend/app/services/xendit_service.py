import httpx
from typing import Dict, Any
from fastapi import HTTPException
from app.core.config import settings

class XenditService:
    def __init__(self):
        self.api_base_url = settings.XENDIT_API_BASE_URL
        self.secret_key = settings.XENDIT_SECRET_KEY
        self.webhook_token = settings.XENDIT_WEBHOOK_TOKEN

    async def create_invoice(self, external_id: str, amount: float, payer_email: str, description: str = "Payment for order") -> Dict[str, Any]:
        """
        Create an invoice in Xendit.
        Returns dict containing 'id', 'invoice_url', etc.
        """
        url = f"{self.api_base_url}/v2/invoices"
        headers = {
            "Content-Type": "application/json"
        }
        auth = (self.secret_key, "")  # Basic Auth dengan username = secret key, password kosong
        payload = {
            "external_id": external_id,
            "amount": amount,
            "payer_email": payer_email,
            "description": description,
            "invoice_duration": 86400,  # 24 jam dalam detik
            "should_send_email": True,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers, auth=auth)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if e.response else str(e)
                raise HTTPException(
                    status_code=502,
                    detail=f"Xendit API error: {error_detail}"
                )
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to connect to Xendit: {str(e)}"
                )

    def verify_webhook_token(self, callback_token: str) -> bool:
        """Verify the webhook callback token from Xendit."""
        return callback_token == self.webhook_token

xendit_service = XenditService()