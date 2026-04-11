"""Stripe API client wrapper."""
import stripe
from agentforge.core.config import settings

stripe.api_key = settings.stripe_secret_key

class StripeClient:
    async def create_checkout_session(self, user_id: str, email: str, price_id: str,
                                       success_url: str, cancel_url: str) -> dict:
        s = stripe.checkout.Session.create(
            customer_email=email, payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}], mode='subscription',
            success_url=success_url, cancel_url=cancel_url, metadata={'user_id': user_id})
        return {'url': s.url, 'id': s.id}

    async def create_portal_session(self, customer_id: str, return_url: str) -> dict:
        s = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
        return {'url': s.url}

    def construct_webhook_event(self, payload: bytes, sig: str) -> dict:
        return stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
