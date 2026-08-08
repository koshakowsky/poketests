"""Billing & checkout — test-cases/11-billing-checkout.md"""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter

from dataset import CARDS
from fixtures.users import future_expiry
from schemas import PlanOut, SubscriptionOut

PLAN_LIST = TypeAdapter(list[PlanOut])


def _card(number=CARDS.visa_ok, cvc="123", month=None, year=None):
    m, y = future_expiry()
    return {
        "number": number,
        "exp_month": m if month is None else month,
        "exp_year": y if year is None else year,
        "cvc": cvc,
    }


def _checkout(api, user, card=None, plan_id="premium", key=None):
    body = {"plan_id": plan_id, "card": card or _card()}
    if key is not None:
        body["idempotency_key"] = key
    return api.post("billing/checkout", headers=user.headers, json=body)


def _error_code(response):
    return response.json()["detail"]["error_code"]


@pytest.mark.p0
def test_plans_are_public(api):
    """TC-BILL-01: plans list is public and well-formed."""
    r = api.get("billing/plans")
    assert r.status_code == 200
    plans = PLAN_LIST.validate_python(r.json())
    premium = next(p for p in plans if p.id == "premium")
    assert premium.price_cents > 0


@pytest.mark.p1
def test_fresh_user_has_no_subscription(api, free_user):
    """TC-BILL-02: a new user has status=none, all other fields null."""
    r = api.get("billing/subscription", headers=free_user.headers)
    assert r.status_code == 200
    sub = SubscriptionOut.model_validate(r.json())
    assert sub.status == "none"
    assert sub.plan is None and sub.card_last4 is None


@pytest.mark.p0
def test_checkout_happy_path(api, free_user):
    """TC-BILL-03: valid card -> 200 active, tier upgraded on the same token."""
    r = _checkout(api, free_user)
    assert r.status_code == 200
    sub = SubscriptionOut.model_validate(r.json())
    assert sub.status == "active"
    assert sub.plan == "premium"
    assert sub.card_brand == "visa"
    assert sub.card_last4 == "4242"

    me = api.get("auth/me", headers=free_user.headers).json()
    assert me["tier"] == "premium"


@pytest.mark.p0
@pytest.mark.parametrize(
    "number, expected_status, expected_code",
    [
        (CARDS.luhn_invalid, 422, "invalid_number"),
        ("424242424242", 422, "invalid_number"),   # 12 digits, below min length
        (CARDS.visa_ok, 200, None),
        ("4242 4242 4242 4242", 200, None),          # formatting is normalized
    ],
    ids=["luhn-fail", "too-short", "valid", "formatted"],
)
def test_checkout_card_number(api, make_user, number, expected_status, expected_code):
    """TC-BILL-04: card number validation (Luhn + length)."""
    r = _checkout(api, make_user(), card=_card(number=number))
    assert r.status_code == expected_status
    if expected_code:
        assert _error_code(r) == expected_code


@pytest.mark.p1
@pytest.mark.parametrize(
    "month, year_delta, expected_status, expected_code",
    [
        (0, 2, 422, "invalid_expiry"),
        (13, 2, 422, "invalid_expiry"),
        (12, -1, 422, "card_expired"),
        (12, 2, 200, None),
    ],
    ids=["month-0", "month-13", "past-year", "future"],
)
def test_checkout_expiry(api, make_user, month, year_delta, expected_status, expected_code):
    """TC-BILL-05: expiry month bounds and past/future date."""
    year = datetime.now(timezone.utc).year + year_delta
    r = _checkout(api, make_user(), card=_card(month=month, year=year))
    assert r.status_code == expected_status
    if expected_code:
        assert _error_code(r) == expected_code


@pytest.mark.p1
@pytest.mark.parametrize(
    "number, cvc, expected_status",
    [
        (CARDS.visa_ok, "12", 422),
        (CARDS.visa_ok, "123", 200),
        (CARDS.visa_ok, "1234", 422),
        (CARDS.amex_ok, "123", 422),
        (CARDS.amex_ok, "1234", 200),
    ],
    ids=["visa-2", "visa-3", "visa-4", "amex-3", "amex-4"],
)
def test_checkout_cvc_length_by_brand(api, make_user, number, cvc, expected_status):
    """TC-BILL-06: CVC length depends on brand (amex 4, others 3)."""
    r = _checkout(api, make_user(), card=_card(number=number, cvc=cvc))
    assert r.status_code == expected_status
    if expected_status == 422:
        assert _error_code(r) == "invalid_cvc"


@pytest.mark.p0
@pytest.mark.parametrize(
    "number, expected_code",
    [(CARDS.declined, "card_declined"), (CARDS.insufficient, "insufficient_funds")],
    ids=["declined", "insufficient"],
)
def test_checkout_declined(api, make_user, number, expected_code):
    """TC-BILL-07: a format-valid card the gateway declines -> 402, user stays free."""
    user = make_user()
    r = _checkout(api, user, card=_card(number=number))
    assert r.status_code == 402
    assert _error_code(r) == expected_code
    assert api.get("auth/me", headers=user.headers).json()["tier"] == "free"
    assert api.get("billing/subscription", headers=user.headers).json()["status"] == "none"


@pytest.mark.p1
def test_checkout_unknown_plan(api, free_user):
    """TC-BILL-08: unknown plan -> 404 (checked before the card)."""
    r = _checkout(api, free_user, plan_id="gold")
    assert r.status_code == 404
    assert _error_code(r) == "unknown_plan"


@pytest.mark.p1
def test_checkout_already_subscribed(api, make_user):
    """TC-BILL-09: a second checkout on an active sub -> 409."""
    user = make_user()
    assert _checkout(api, user).status_code == 200
    again = _checkout(api, user)
    assert again.status_code == 409
    assert _error_code(again) == "already_subscribed"


@pytest.mark.p1
def test_checkout_precedence_plan_before_card(api, free_user):
    """TC-BILL-10: unknown plan wins over an invalid card (404, not 422)."""
    r = _checkout(api, free_user, card=_card(number=CARDS.luhn_invalid), plan_id="gold")
    assert r.status_code == 404
    assert _error_code(r) == "unknown_plan"


@pytest.mark.p1
def test_checkout_idempotency_replays_result(api, make_user):
    """TC-BILL-11: same idempotency_key returns the identical body (same
    period_end) — the stored response is replayed, not recomputed."""
    user = make_user()
    key = uuid.uuid4().hex
    first = _checkout(api, user, key=key)
    assert first.status_code == 200
    second = _checkout(api, user, key=key)
    assert second.status_code == 200
    assert second.json() == first.json()


@pytest.mark.p1
def test_subscription_reflects_masked_card(api, make_user):
    """TC-BILL-12 / TC-BILL-17: only brand + last4 are exposed, never the PAN/CVC."""
    user = make_user()
    _checkout(api, user)
    r = api.get("billing/subscription", headers=user.headers)
    sub = SubscriptionOut.model_validate(r.json())
    assert sub.status == "active"
    assert sub.card_brand == "visa"
    assert sub.card_last4 == "4242"
    assert CARDS.visa_ok not in r.text  # full number never leaks


@pytest.mark.p0
def test_cancel_downgrades(api, make_user):
    """TC-BILL-13: cancel an active sub -> 200 canceled, tier back to free."""
    user = make_user()
    _checkout(api, user)
    r = api.post("billing/cancel", headers=user.headers)
    assert r.status_code == 200
    assert r.json()["status"] == "canceled"
    assert api.get("auth/me", headers=user.headers).json()["tier"] == "free"


@pytest.mark.p1
def test_cancel_without_active(api, free_user):
    """TC-BILL-14: cancel with nothing active -> 409."""
    r = api.post("billing/cancel", headers=free_user.headers)
    assert r.status_code == 409
    assert _error_code(r) == "no_active_subscription"


@pytest.mark.p1
def test_reactivation_after_cancel(api, make_user):
    """TC-BILL-15: checkout -> cancel -> checkout again -> active premium."""
    user = make_user()
    _checkout(api, user)
    api.post("billing/cancel", headers=user.headers)
    again = _checkout(api, user)
    assert again.status_code == 200
    assert again.json()["status"] == "active"
    assert api.get("auth/me", headers=user.headers).json()["tier"] == "premium"


@pytest.mark.p2
@pytest.mark.parametrize(
    "body",
    [{"plan_id": "premium"}, {"card": {"number": CARDS.visa_ok, "exp_month": 12, "exp_year": 2030, "cvc": "123"}}],
    ids=["no-card", "no-plan"],
)
def test_checkout_body_validation(api, free_user, body):
    """TC-BILL-16: missing required fields -> 422 (framework validation)."""
    r = api.post("billing/checkout", headers=free_user.headers, json=body)
    assert r.status_code == 422


@pytest.mark.p2
def test_amex_happy_path(api, make_user):
    """TC-BILL-18: amex with a 4-digit CVC -> 200, brand amex, last4 0005."""
    r = _checkout(api, make_user(), card=_card(number=CARDS.amex_ok, cvc="1234"))
    assert r.status_code == 200
    sub = SubscriptionOut.model_validate(r.json())
    assert sub.card_brand == "amex"
    assert sub.card_last4 == "0005"
