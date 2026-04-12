"""Stripe client helpers — thin wrappers used by billing routes."""
import stripe
from agentforge.core.config import settings

stripe.api_key = settings.stripe_secret_key


def get_checkout_session(session_id: str) -> stripe.checkout.Session:
    """Retrieve a Stripe checkout session by ID."""
    return stripe.checkout.Session.retrieve(session_id)


def list_session_line_items(session_id: str, limit: int = 5):
    """List line items for a completed checkout session."""
    return stripe.checkout.Session.list_line_items(session_id, limit=limit)


def create_checkout_session(
    customer_email: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    user_id: str,
) -> stripe.checkout.Session:
    """Create a Stripe checkout session for a subscription plan."""
    return stripe.checkout.Session.create(
        customer_email=customer_email,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user_id},
    )


def create_portal_session(customer_id: str, return_url: str) -> stripe.billing_portal.Session:
    """Create a Stripe billing portal session for subscription management."""
    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )


def construct_webhook_event(payload: bytes, sig: str, secret: str) -> stripe.Event:
    """Verify and construct a Stripe webhook event."""
    return stripe.Webhook.construct_event(payload, sig, secret)
