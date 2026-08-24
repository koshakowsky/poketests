"""Billing test-data builders.

Not fixtures - plain builders, so a test picks a card number from
dataset.CARDS and nothing else has to know the body shape. Kept next to the
fixtures because that is what they feed.
"""

from datetime import datetime, timezone

from dataset import CARDS


def future_expiry() -> tuple[int, int]:
    """A safely-future (month, year), derived from the run date.

    Computed rather than hardcoded so the suite does not start failing on its
    own once a pinned year goes past.
    """
    return 12, datetime.now(timezone.utc).year + 2


def build_card(number: str = CARDS.visa_ok, cvc: str = "123", month=None, year=None) -> dict:
    """A checkout card body. Overrides are explicit-None so that month=0 (an
    invalid-expiry case) is passed through instead of being treated as unset.
    """
    default_month, default_year = future_expiry()
    return {
        "number": number,
        "exp_month": default_month if month is None else month,
        "exp_year": default_year if year is None else year,
        "cvc": cvc,
    }
