"""Stripe billing routes: checkout, portal, webhook."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from agentforge.db.models import User
from agentforge.auth.deps import get_current_user
from agentforge.billing.stripe_client import StripeClient

router = APIRouter()
stripe_client = StripeClient()

PLAN_PRICES = {
    'pro': 'price_pro_monthly',
    'teams': 'price_teams_monthly',
    'enterprise': 'price_enterprise_monthly',
}


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str = 'http://localhost:3000/billing/success'
    cancel_url: str = 'http://localhost:3000/billing/cancel'


@router.post('/checkout')
async def create_checkout(body: CheckoutRequest, user: User = Depends(get_current_user)):
    price_id = PLAN_PRICES.get(body.plan)
    if not price_id:
        raise HTTPException(400, f'Unknown plan: {body.plan}')
    session = await stripe_client.create_checkout_session(
        user_id=str(user.id), email=user.email, price_id=price_id,
        success_url=body.success_url, cancel_url=body.cancel_url,
    )
    return {'checkout_url': session['url'], 'session_id': session['id']}


@router.post('/portal')
async def billing_portal(user: User = Depends(get_current_user)):
    if not user.stripe_customer_id:
        raise HTTPException(400, 'No billing account found')
    portal = await stripe_client.create_portal_session(
        customer_id=user.stripe_customer_id, return_url='http://localhost:3000/settings')
    return {'portal_url': portal['url']}


@router.post('/webhook')
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get('stripe-signature', '')
    event = stripe_client.construct_webhook_event(payload, sig)
    if event['type'] == 'checkout.session.completed':
        pass  # update user plan in DB
    return {'received': True}
