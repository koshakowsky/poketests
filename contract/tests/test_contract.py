"""Contract - schemathesis against the live OpenAPI schema (README pyramid).

Every operation is fuzzed with schema-derived data and the response is checked
against the schema. We run a deliberate subset of checks:

- not_a_server_error - the headline: no input should ever yield a 500.
- response_schema_conformance - a documented response body matches the schema.
- content_type_conformance - the response content type is one the schema allows.

status_code_conformance is intentionally NOT run: FastAPI only auto-documents
200/201 and the 422 validation error, not the business codes (401/403/404/409),
so it would flag every legitimate error response as "undocumented". The three
checks above are the ones that catch real contract breaks.
"""

import schemathesis
from hypothesis import settings
from schemathesis.checks import content_type_conformance, not_a_server_error, response_schema_conformance

schema = schemathesis.from_pytest_fixture("openapi_schema")

CHECKS = (not_a_server_error, response_schema_conformance, content_type_conformance)


@schema.parametrize()
@settings(max_examples=20, deadline=None)
def test_contract(case, contract_headers):
    case.call_and_validate(checks=CHECKS, headers=contract_headers)
