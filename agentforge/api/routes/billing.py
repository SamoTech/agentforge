"""Billing routes — Stripe checkout, portal, webhooks."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from agentforge.auth.deps import get_current_user
from agentforge.db.models import User
from agentforge.billing.stripe_client import StripeClient
from agentforge.core.config import settings

router = APIRouter()
stripe_client = StripeClient()

class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str = 'https://app.agentforge.dev/billing/success'
    cancel_url: str = 'https://app.agentforge.dev/billing/cancel'

@router.post('/checkout')
async def create_checkout(body: CheckoutRequest, user: User = Depends(get_current_user)):
    session = await stripe_client.create_checkout_session(
        user_id=str(user.id), email=user.email, price_id=body.price_id,
        success_url=body.success_url, cancel_url=body.cancel_url)
    return session

@router.post('/portal')
async def create_portal(user: User = Depends(get_current_user)):
    if not user.stripe_customer_id: raise HTTPException(400, 'No Stripe customer found')
    session = await stripe_client.create_portal_session(
        customer_id=user.stripe_customer_id, return_url='https://app.agentforge.dev/billing')
    return session

@router.post('/webhook')
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get('stripe-signature', '')
    try:
        event = stripe_client.construct_webhook_event(payload, sig)
    except Exception:
        raise HTTPException(400, 'Invalid webhook signature')
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # TODO: update user plan in DB
        pass
    return {'status': 'received'}
