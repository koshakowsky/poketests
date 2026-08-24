"""Contract-suite fixtures.

Loads the live OpenAPI schema for schemathesis and provides a premium bearer so
the gated operations are fuzzed as an authorized caller (not just bounced at
401). The shared root conftest still applies - its canary is a valid
precondition here too.
"""

import os

import pytest
import schemathesis

BASE_URL = os.getenv("POKETESTS_BASE_URL", "http://localhost/api").rstrip("/")


@pytest.fixture(scope="session")
def openapi_schema():
    # FastAPI emits OpenAPI 3.1; force_schema_version coerces it to the 3.0
    # dialect schemathesis 3.x fully supports.
    return schemathesis.from_uri(f"{BASE_URL}/openapi.json", force_schema_version="30")


@pytest.fixture(scope="session")
def contract_headers(premium_token) -> dict:
    return {"Authorization": f"Bearer {premium_token}"}
