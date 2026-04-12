"""Stripe billing: checkout, portal, webhook."""
import uuid
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from agentforge.db.base import get_db
from agentforge.db.models import User
from agentforge.auth.deps import get_current_user
from agentforge.core.config import settings
from agentforge.core.logger import logger

stripe.api_key = settings.stripe_secret_key
router = APIRouter()

PLAN_PRICES = {
    "pro":        "price_pro_monthly",
    "teams":      "price_teams_monthly",
    "enterprise": "price_enterprise_monthly",
}

# Reverse-map price_id → plan name for webhook lookups
PRICE_TO_PLAN = {v: k for k, v in PLAN_PRICES.items()}


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
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)

    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data, db)

    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)

    logger.info("stripe_webhook", event_type=event_type)
    return {"received": True}


async def _handle_checkout_completed(session: dict, db: AsyncSession) -> None:
    """Upgrade user plan and persist Stripe customer ID after successful checkout."""
    user_id_str = (session.get("metadata") or {}).get("user_id")
    if not user_id_str:
        logger.warning("stripe_webhook_no_user_id", session_id=session.get("id"))
        return

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        logger.error("stripe_webhook_bad_uuid", raw=user_id_str)
        return

    user: User | None = await db.get(User, user_id)
    if not user:
        logger.error("stripe_webhook_user_not_found", user_id=user_id_str)
        return

    # Determine which plan was purchased from the first line item price
    line_items = stripe.checkout.Session.list_line_items(session["id"], limit=1)
    new_plan = "pro"  # safe default
    if line_items and line_items.data:
        price_id = line_items.data[0].price.id
        new_plan = PRICE_TO_PLAN.get(price_id, "pro")

    user.plan = new_plan
    # Store Stripe customer ID for future portal/subscription management
    if session.get("customer") and not user.stripe_customer_id:
        user.stripe_customer_id = session["customer"]

    await db.commit()
    logger.info("user_plan_upgraded", user_id=user_id_str, plan=new_plan)


async def _handle_subscription_updated(subscription: dict, db: AsyncSession) -> None:
    """Sync plan when Stripe subscription changes (upgrade/downgrade)."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        return

    # Grab price from first subscription item
    items = (subscription.get("items") or {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")
        user.plan = PRICE_TO_PLAN.get(price_id, user.plan)
        await db.commit()
        logger.info("user_plan_synced", customer=customer_id, plan=user.plan)


async def _handle_subscription_deleted(subscription: dict, db: AsyncSession) -> None:
    """Downgrade user to free plan when subscription is cancelled."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        return

    user.plan = "free"
    await db.commit()
    logger.info("user_plan_downgraded", customer=customer_id)
