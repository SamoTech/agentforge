"""Stripe billing: checkout, portal, webhook."""
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from agentforge.db.models import User
from agentforge.auth.deps import get_current_user
from agentforge.core.config import settings

stripe.api_key = settings.stripe_secret_key
router = APIRouter()

PLAN_PRICES = {
    "pro":        "price_pro_monthly",
    "teams":      "price_teams_monthly",
    "enterprise": "price_enterprise_monthly",
}


class CheckoutReq(BaseModel):
    plan: str
    success_url: str = "http://localhost:3000/billing/success"
    cancel_url:  str = "http://localhost:3000/billing/cancel"


@router.post("/checkout")
async def checkout(body: CheckoutReq, user: User = Depends(get_current_user)):
    price_id = PLAN_PRICES.get(body.plan)
    if not price_id:
        raise HTTPException(400, f"Unknown plan: {body.plan}")
    session = stripe.checkout.Session.create(
        customer_email=user.email,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"user_id": str(user.id)},
    )
    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal")
async def portal(user: User = Depends(get_current_user)):
    if not user.stripe_customer_id:
        raise HTTPException(400, "No billing account")
    s = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id, return_url="http://localhost:3000/settings"
    )
    return {"portal_url": s.url}


@router.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig     = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    if event["type"] == "checkout.session.completed":
        _session = event["data"]["object"]
        # TODO: update user.plan in DB via session.metadata["user_id"]
        pass
    return {"received": True}
