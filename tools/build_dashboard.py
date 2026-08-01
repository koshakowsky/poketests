"""Generate the project-health dashboard (index.html) from Allure results.

Live metrics (test counts, pass rate, P0-P3 breakdown) are parsed from the
`*-result.json` files the suite already produces via `pytest --alluredir`
(status + our severity labels) — no extra plugin or artifact. Structural facts
(pyramid, endpoint coverage, bug lifecycle, stack) are maintained as constants
below; they change rarely and deliberately.

Usage (CI):
    python tools/build_dashboard.py <allure-results-dir> <out.html>
Run metadata comes from the environment (GITHUB_* + BUILD_TIME).
"""

import glob
import html
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

# --- Structural facts (maintained by hand; change rarely) --------------------

SUT_ENDPOINTS = [
    ("GET /api/health", True),
    ("GET /api/pokemon/", True),
    ("GET /api/pokemon/search", True),
    ("GET /api/pokemon/{id}", True),
    ("GET /api/pokemon/{id}/similar", True),
    ("POST /api/compare/", True),
    ("GET /api/analytics/categories", True),
    ("GET /api/analytics/type-distribution", True),
    ("GET /api/analytics/stat-ranges", True),
    ("GET /api/analytics/generation-stats", True),
    ("GET /api/types/", True),
    ("GET /api/types/{id}/effectiveness", True),
    ("POST /api/admin/seed", True),
]

PYRAMID = [
    ("E2E (Playwright)", "planned", "UI journeys — next milestone"),
    ("API / integration", "active", "this suite — router + service + DB over HTTP"),
    ("Contract", "planned", "schemathesis against the live OpenAPI schema"),
    ("Unit", "partial", "pure functions + pytest smoke in the SUT repo"),
]

BUGS = [
    ("BUG-001", "LIKE-wildcard injection in the name filter", "fixed"),
    ("BUG-002", "Unstable pagination (no sort tiebreaker)", "fixed"),
]

TECHNIQUES = ["EP", "BVA", "Pairwise", "Decision tables", "Error guessing", "State/seq"]
STACK = ["Python", "pytest", "httpx", "pydantic", "allpairspy", "Allure", "Docker", "GitHub Actions"]

LINKS = [
    ("Full Allure report", "allure/"),
    ("Test-case catalog", "https://github.com/koshakowsky/poketests/tree/main/test-cases"),
    ("Bug reports", "https://github.com/koshakowsky/poketests/tree/main/bugs"),
    ("CI workflow", "https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml"),
    ("System under test", "https://github.com/koshakowsky/pokeanalytics"),
]

# Allure status -> our bucket
_STATUS_BUCKET = {"passed": "passed", "failed": "failed", "broken": "failed",
                  "skipped": "skipped"}
# Allure severity (from our p0-p3 mapping) -> priority label
_SEVERITY_TO_PRIO = {"blocker": "P0", "critical": "P1", "normal": "P2", "minor": "P3"}


def parse_results(results_dir: str) -> dict:
    buckets = Counter()
    prios = Counter()
    for path in glob.glob(os.path.join(results_dir, "*-result.json")):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        buckets[_STATUS_BUCKET.get(data.get("status"), "other")] += 1
        for label in data.get("labels", []):
            if label.get("name") == "severity":
                prios[_SEVERITY_TO_PRIO.get(label["value"], "?")] += 1
    total = sum(buckets.values())
    passed = buckets["passed"]
    # Pass rate over executed (non-skipped) tests — skips are not failures.
    executed = total - buckets["skipped"]
    pass_rate = round(passed / executed * 100, 1) if executed else 0.0
    return {
        "total": total,
        "passed": passed,
        "failed": buckets["failed"],
        "skipped": buckets["skipped"],
        "pass_rate": pass_rate,
        "prios": prios,
    }


# --- Rendering ---------------------------------------------------------------

def _tile(value, label, tone="ink"):
    return f'<div class="tile {tone}"><div class="tile-v">{value}</div><div class="tile-l">{html.escape(label)}</div></div>'


def _status_pill(state: str) -> str:
    tone = {"active": "good", "partial": "warn", "planned": "muted",
            "fixed": "good"}.get(state, "muted")
    return f'<span class="pill {tone}">{html.escape(state)}</span>'


def render(m: dict) -> str:
    run = os.getenv("GITHUB_RUN_NUMBER", "local")
    sha = (os.getenv("GITHUB_SHA", "") or "")[:7]
    when = os.getenv("BUILD_TIME") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    prio_rows = "".join(
        f'<div class="pr"><span class="pr-k">{p}</span>'
        f'<span class="pr-bar"><span style="width:{(m["prios"].get(p,0)/max(m["total"],1))*100:.0f}%"></span></span>'
        f'<span class="pr-n">{m["prios"].get(p,0)}</span></div>'
        for p in ("P0", "P1", "P2", "P3")
    )
    pyramid_rows = "".join(
        f'<div class="row"><span class="row-k">{html.escape(name)}</span>'
        f'{_status_pill(state)}<span class="row-d">{html.escape(desc)}</span></div>'
        for name, state, desc in PYRAMID
    )
    cov_done = sum(1 for _, ok in SUT_ENDPOINTS if ok)
    cov_rows = "".join(
        f'<li class="{("ok" if ok else "no")}">{html.escape(ep)}</li>'
        for ep, ok in SUT_ENDPOINTS
    )
    bug_rows = "".join(
        f'<div class="row"><span class="row-k">{html.escape(bid)}</span>'
        f'{_status_pill(state)}<span class="row-d">{html.escape(desc)}</span></div>'
        for bid, desc, state in BUGS
    )
    chips = lambda xs: "".join(f'<span class="chip">{html.escape(x)}</span>' for x in xs)
    links = "".join(
        f'<a class="lnk" href="{html.escape(href)}">{html.escape(text)} →</a>'
        for text, href in LINKS
    )

    rate_tone = "good" if m["pass_rate"] >= 100 else "warn" if m["pass_rate"] >= 90 else "bad"

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PokéAnalytics — Test Health</title>
<style>
:root {{
  --bg:#f7f8fa; --surface:#ffffff; --ink:#0f172a; --ink2:#475569; --muted:#94a3b8;
  --line:#e2e8f0; --good:#16a34a; --warn:#d97706; --bad:#dc2626; --accent:#4f46e5;
  --track:#eef2f7;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#0b1020; --surface:#131a2b; --ink:#e8edf6; --ink2:#9fb0c8;
    --muted:#64748b; --line:#243147; --track:#1c2740; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
.wrap {{ max-width:1040px; margin:0 auto; padding:32px 20px 56px; }}
header {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 14px; margin-bottom:6px; }}
h1 {{ font-size:24px; margin:0; letter-spacing:-.02em; }}
.sub {{ color:var(--ink2); font-size:13px; }}
.meta {{ color:var(--muted); font-size:12px; margin-bottom:24px; }}
.grid {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); }}
.card {{ background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:18px 20px; }}
.card h2 {{ font-size:12px; text-transform:uppercase; letter-spacing:.06em;
  color:var(--muted); margin:0 0 14px; }}
.hero {{ display:flex; align-items:baseline; gap:10px; }}
.hero .big {{ font-size:44px; font-weight:800; letter-spacing:-.03em; line-height:1; }}
.hero.good .big {{ color:var(--good); }} .hero.warn .big {{ color:var(--warn); }}
.hero.bad .big {{ color:var(--bad); }}
.hero .u {{ color:var(--ink2); font-size:14px; }}
.bar {{ display:flex; height:10px; border-radius:6px; overflow:hidden; margin-top:14px; gap:2px; background:var(--track); }}
.bar i {{ display:block; }} .bar .p {{ background:var(--good); }} .bar .s {{ background:var(--warn); }} .bar .f {{ background:var(--bad); }}
.legend {{ display:flex; gap:14px; margin-top:10px; font-size:12px; color:var(--ink2); }}
.legend b {{ color:var(--ink); }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:5px; vertical-align:middle; }}
.tiles {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }}
.tile {{ background:var(--track); border-radius:10px; padding:12px; text-align:center; }}
.tile-v {{ font-size:22px; font-weight:700; }} .tile-l {{ font-size:11px; color:var(--ink2); margin-top:2px; }}
.pr {{ display:grid; grid-template-columns:34px 1fr 30px; align-items:center; gap:10px; margin:8px 0; }}
.pr-k {{ font-size:12px; font-weight:600; color:var(--ink2); }}
.pr-bar {{ background:var(--track); border-radius:5px; height:8px; overflow:hidden; }}
.pr-bar span {{ display:block; height:100%; background:var(--accent); border-radius:5px; }}
.pr-n {{ text-align:right; font-variant-numeric:tabular-nums; font-size:13px; }}
.row {{ display:flex; align-items:center; gap:10px; padding:7px 0; border-top:1px solid var(--line); flex-wrap:wrap; }}
.row:first-of-type {{ border-top:none; }}
.row-k {{ font-weight:600; font-size:13px; min-width:120px; }}
.row-d {{ color:var(--ink2); font-size:12px; }}
.pill {{ font-size:11px; padding:2px 8px; border-radius:999px; font-weight:600; }}
.pill.good {{ color:var(--good); background:color-mix(in srgb,var(--good) 14%,transparent); }}
.pill.warn {{ color:var(--warn); background:color-mix(in srgb,var(--warn) 14%,transparent); }}
.pill.muted {{ color:var(--muted); background:color-mix(in srgb,var(--muted) 16%,transparent); }}
ul.cov {{ list-style:none; margin:0; padding:0; columns:2; font-size:12px; }}
ul.cov li {{ padding:3px 0 3px 20px; position:relative; color:var(--ink2); break-inside:avoid; }}
ul.cov li.ok::before {{ content:"✓"; color:var(--good); position:absolute; left:0; font-weight:700; }}
ul.cov li.no::before {{ content:"·"; color:var(--muted); position:absolute; left:2px; }}
.chip {{ display:inline-block; font-size:12px; padding:3px 10px; margin:0 6px 6px 0;
  background:var(--track); border-radius:999px; color:var(--ink2); }}
.links {{ display:flex; flex-wrap:wrap; gap:8px 18px; margin-top:8px; }}
.lnk {{ color:var(--accent); text-decoration:none; font-size:13px; font-weight:600; }}
.lnk:hover {{ text-decoration:underline; }}
.full {{ grid-column:1/-1; }}
footer {{ margin-top:28px; color:var(--muted); font-size:12px; text-align:center; }}
</style></head><body><div class="wrap">
<header><h1>◓ PokéAnalytics — Test Health</h1>
<span class="sub">API test suite · project dashboard</span></header>
<div class="meta">Generated from CI run #{html.escape(str(run))}{(' · ' + sha) if sha else ''} · {html.escape(when)}</div>

<div class="grid">
  <div class="card">
    <h2>Pass rate</h2>
    <div class="hero {rate_tone}"><span class="big">{m['pass_rate']:.0f}%</span>
      <span class="u">of {m['total']-m['skipped']} executed</span></div>
    <div class="bar">
      <i class="p" style="flex:{max(m['passed'],0)}"></i>
      <i class="s" style="flex:{max(m['skipped'],0)}"></i>
      <i class="f" style="flex:{max(m['failed'],0)}"></i>
    </div>
    <div class="legend">
      <span><span class="dot" style="background:var(--good)"></span>Passed <b>{m['passed']}</b></span>
      <span><span class="dot" style="background:var(--warn)"></span>Skipped <b>{m['skipped']}</b></span>
      <span><span class="dot" style="background:var(--bad)"></span>Failed <b>{m['failed']}</b></span>
    </div>
  </div>

  <div class="card">
    <h2>Suite at a glance</h2>
    <div class="tiles">
      {_tile(m['total'], 'total tests')}
      {_tile(len([e for e in SUT_ENDPOINTS if e[1]]), 'endpoints')}
      {_tile(len(BUGS), 'bugs fixed')}
    </div>
    <div class="tiles" style="margin-top:10px">
      {_tile(m['prios'].get('P0',0), 'P0 smoke')}
      {_tile(len(TECHNIQUES), 'techniques')}
      {_tile(m['failed'], 'failing', 'ink')}
    </div>
  </div>

  <div class="card">
    <h2>By priority</h2>
    {prio_rows}
  </div>

  <div class="card full">
    <h2>Test pyramid</h2>
    {pyramid_rows}
  </div>

  <div class="card">
    <h2>Endpoint coverage · {cov_done}/{len(SUT_ENDPOINTS)}</h2>
    <ul class="cov">{cov_rows}</ul>
  </div>

  <div class="card">
    <h2>Defects — full lifecycle</h2>
    {bug_rows}
    <div class="row-d" style="margin-top:8px">Found by test design → reported → xfail → fixed → regression guard.</div>
  </div>

  <div class="card full">
    <h2>Techniques &amp; stack</h2>
    <div style="margin-bottom:10px">{chips(TECHNIQUES)}</div>
    <div>{chips(STACK)}</div>
  </div>

  <div class="card full">
    <h2>Explore</h2>
    <div class="links">{links}</div>
  </div>
</div>
<footer>Auto-generated by tools/build_dashboard.py on every push to main.</footer>
</div></body></html>
"""


def main() -> None:
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "allure-results"
    out = sys.argv[2] if len(sys.argv) > 2 else "index.html"
    metrics = parse_results(results_dir)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(metrics))
    print(f"Wrote {out} — {metrics['total']} tests, "
          f"{metrics['passed']} passed / {metrics['skipped']} skipped / {metrics['failed']} failed, "
          f"pass rate {metrics['pass_rate']}%")


if __name__ == "__main__":
    main()
