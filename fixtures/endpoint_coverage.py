"""Measured endpoint coverage.

Which documented API operations the suites actually exercise, recorded rather
than declared. Every httpx client the suites use is built here, with a response
hook that notes the (method, path) it just called; the canary contributes the
set of documented operations from the SUT's live OpenAPI schema. At the end of
a session the two sets are written next to the Allure results, and the dashboard
unions them across suites and xdist workers.

Concrete paths are folded back into their OpenAPI template (/api/pokemon/25 ->
/api/pokemon/{pokemon_id}) so a request counts against the operation it hit.
"""

import json
import os
import re
import uuid
from pathlib import Path

import httpx

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

# (METHOD, concrete path) actually requested, and (METHOD, template) documented.
_hits: set[tuple[str, str]] = set()
_documented: set[tuple[str, str]] = set()


def record_documented(schema: dict) -> None:
    """Take the operation list from a fetched OpenAPI document."""
    for path, operations in (schema.get("paths") or {}).items():
        for method in operations:
            if method.lower() in HTTP_METHODS:
                _documented.add((method.upper(), path))


def _note(response: httpx.Response) -> None:
    _hits.add((response.request.method.upper(), response.request.url.path))


def client(base_url, **kwargs) -> httpx.Client:
    """The one place suites get an HTTP client, so nothing escapes the recorder."""
    hooks = kwargs.pop("event_hooks", {})
    hooks.setdefault("response", []).append(_note)
    return httpx.Client(base_url=base_url, event_hooks=hooks, **kwargs)


def _template_matcher(template: str) -> re.Pattern:
    pattern = re.sub(r"\{[^/}]+\}", "[^/]+", re.escape(template).replace(r"\{", "{").replace(r"\}", "}"))
    return re.compile(f"^{pattern}$")


def resolve(hits, documented):
    """Fold concrete paths into templates; returns the covered operation set.

    When several templates match, the most literal one wins - otherwise
    /api/pokemon/search would be credited to /api/pokemon/{pokemon_id}.
    """
    templates = sorted(
        {path for _, path in documented},
        key=lambda p: (p.count("{"), -len(p)),
    )
    matchers = [(t, _template_matcher(t)) for t in templates]

    covered = set()
    for method, path in hits:
        for template, matcher in matchers:
            if matcher.match(path) and (method, template) in documented:
                covered.add((method, template))
                break
    return covered


def write(config) -> None:
    """Dump this process's sets next to the Allure results, if any."""
    alluredir = getattr(config.option, "allure_report_dir", None)
    if not alluredir or not (_hits or _documented):
        return
    target = Path(alluredir)
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "hits": sorted([m, p] for m, p in _hits),
        "documented": sorted([m, p] for m, p in _documented),
    }
    # A unique name per writing process: suites are merged into one directory
    # in CI, and xdist worker ids repeat across them (gw0 from api would clobber
    # gw0 from e2e).
    name = f"endpoint-coverage-{os.environ.get('PYTEST_XDIST_WORKER', 'main')}-{uuid.uuid4().hex[:8]}.json"
    (target / name).write_text(json.dumps(payload), encoding="utf-8")
