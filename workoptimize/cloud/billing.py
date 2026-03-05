"""Stripe billing integration for the SaaS subscription model.

Pricing tiers:
- Free: Basic suggestions, 50 captures/day, manual ask
- Pro ($19/mo): Unlimited captures, pattern tracking, automation builder, cloud sync
- Team ($49/mo/user): Everything in Pro + team dashboard, admin controls, aggregate reports

This module handles client-side billing operations. The actual Stripe
webhook processing happens on your cloud backend.
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PlanId(Enum):
    FREE = "free"
    PRO_MONTHLY = "pro_monthly"
    PRO_ANNUAL = "pro_annual"
    TEAM_MONTHLY = "team_monthly"
    TEAM_ANNUAL = "team_annual"


@dataclass
class PlanDetails:
    id: PlanId
    name: str
    price_monthly: float
    price_annual: float
    features: list[str]
    capture_limit: int  # 0 = unlimited
    stripe_price_id_monthly: str
    stripe_price_id_annual: str


# Plan catalog
PLANS = {
    PlanId.FREE: PlanDetails(
        id=PlanId.FREE,
        name="Free",
        price_monthly=0,
        price_annual=0,
        features=[
            "Basic suggestions",
            "50 screen captures per day",
            "Ask about your screen",
        ],
        capture_limit=50,
        stripe_price_id_monthly="",
        stripe_price_id_annual="",
    ),
    PlanId.PRO_MONTHLY: PlanDetails(
        id=PlanId.PRO_MONTHLY,
        name="Pro",
        price_monthly=19.0,
        price_annual=190.0,
        features=[
            "Unlimited captures",
            "Pattern tracking & insights",
            "Automation builder",
            "Cloud sync",
            "Focus score analytics",
            "Priority support",
        ],
        capture_limit=0,
        stripe_price_id_monthly="price_pro_monthly_placeholder",
        stripe_price_id_annual="price_pro_annual_placeholder",
    ),
    PlanId.TEAM_MONTHLY: PlanDetails(
        id=PlanId.TEAM_MONTHLY,
        name="Team",
        price_monthly=49.0,
        price_annual=490.0,
        features=[
            "Everything in Pro",
            "Team dashboard",
            "Admin controls",
            "Aggregate reports",
            "SSO integration",
            "Dedicated support",
        ],
        capture_limit=0,
        stripe_price_id_monthly="price_team_monthly_placeholder",
        stripe_price_id_annual="price_team_annual_placeholder",
    ),
}


@dataclass
class SubscriptionStatus:
    plan: PlanId
    active: bool
    current_period_end: float | None
    cancel_at_period_end: bool
    captures_today: int
    capture_limit: int

    @property
    def captures_remaining(self) -> int | None:
        if self.capture_limit == 0:
            return None  # Unlimited
        return max(0, self.capture_limit - self.captures_today)

    @property
    def is_at_limit(self) -> bool:
        if self.capture_limit == 0:
            return False
        return self.captures_today >= self.capture_limit


class BillingManager:
    """Client-side billing state management.

    Flow:
    1. User clicks "Upgrade to Pro" in the app
    2. App opens a Stripe Checkout session URL in the browser
    3. User completes payment on Stripe's hosted page
    4. Your backend receives the Stripe webhook → updates the user's plan
    5. App polls /api/auth/status to detect the plan change
    6. App unlocks Pro features
    """

    def __init__(self, billing_api_url: str = "", auth_token: str | None = None):
        self._api_url = billing_api_url
        self._auth_token = auth_token
        self._captures_today = 0
        self._day_start: float = 0.0
        self._current_plan = PlanId.FREE

    def record_capture(self) -> bool:
        """Record a capture and check if the user is within their plan limits.

        Returns True if the capture is allowed, False if at limit.
        """
        # Reset daily counter
        now = time.time()
        if now - self._day_start > 86400:
            self._captures_today = 0
            self._day_start = now

        plan = PLANS.get(self._current_plan, PLANS[PlanId.FREE])
        if plan.capture_limit > 0 and self._captures_today >= plan.capture_limit:
            return False

        self._captures_today += 1
        return True

    def get_status(self) -> SubscriptionStatus:
        plan = PLANS.get(self._current_plan, PLANS[PlanId.FREE])
        return SubscriptionStatus(
            plan=self._current_plan,
            active=True,
            current_period_end=None,
            cancel_at_period_end=False,
            captures_today=self._captures_today,
            capture_limit=plan.capture_limit,
        )

    def set_plan(self, plan_id: PlanId) -> None:
        self._current_plan = plan_id

    async def create_checkout_url(self, plan_id: PlanId, annual: bool = False) -> str:
        """Generate a Stripe Checkout URL for upgrading.

        In production, this calls your backend:
        POST {api_url}/api/v1/billing/checkout
        Body: { plan_id, annual, return_url }
        Response: { checkout_url }

        Your backend creates the Stripe Checkout Session and returns the URL.
        """
        plan = PLANS.get(plan_id)
        if not plan:
            raise ValueError(f"Unknown plan: {plan_id}")

        price_id = plan.stripe_price_id_annual if annual else plan.stripe_price_id_monthly
        logger.info("Would create checkout for price: %s", price_id)

        # Placeholder — implement with httpx call to your backend
        return f"https://checkout.stripe.com/placeholder/{price_id}"

    async def create_portal_url(self) -> str:
        """Generate a Stripe Customer Portal URL for managing subscription.

        POST {api_url}/api/v1/billing/portal
        Response: { portal_url }
        """
        logger.info("Would create billing portal URL")
        return "https://billing.stripe.com/placeholder/portal"

    @staticmethod
    def get_plans() -> list[dict]:
        """Get all available plans for display."""
        result = []
        for plan in PLANS.values():
            if plan.id in (PlanId.PRO_ANNUAL, PlanId.TEAM_ANNUAL):
                continue  # Don't list annual separately
            result.append({
                "id": plan.id.value,
                "name": plan.name,
                "price_monthly": plan.price_monthly,
                "price_annual": plan.price_annual,
                "features": plan.features,
                "capture_limit": plan.capture_limit,
            })
        return result
