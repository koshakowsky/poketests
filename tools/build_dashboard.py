"""Generate the project-health dashboard (index.html).

Allure already answers "did this run pass?". This page answers the questions it
structurally cannot: how much of the designed catalog is actually executed,
which test-design techniques the catalog applies and how heavily, how the work
splits across the pyramid, and how each defect was found.

Everything on the page is derived at build time from files in this repo -
the Allure results of the run, the test-case catalog, the test sources and the
bug reports. The only hand-maintained parts are the pyramid narrative and the
stack list, which describe intent rather than measurement.

Usage (CI):
    python tools/build_dashboard.py <allure-results-dir> <out.html>
Run metadata comes from the environment (GITHUB_* + BUILD_TIME).
"""

import glob
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- Narrative constants (intent, not measurement) ---------------------------

PYRAMID = [
    ("E2E (Playwright)", "UI journeys over Page Objects; thin by design"),
    ("Contract", "schemathesis fuzzes every operation from the live OpenAPI schema"),
    ("API / integration", "the bulk of the suite: router + service + DB over HTTP"),
    ("Unit", "pure functions + pytest smoke, in the SUT repo"),
]

STACK = ["Python", "pytest", "httpx", "Playwright", "schemathesis", "axe-core",
         "pydantic", "allpairspy", "pytest-xdist", "Allure", "Docker", "GitHub Actions"]

LINKS = [
    ("Full Allure report", "allure/"),
    ("Test-case catalog", "https://github.com/koshakowsky/poketests/tree/main/test-cases"),
    ("Bug reports", "https://github.com/koshakowsky/poketests/tree/main/bugs"),
    ("CI workflow", "https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml"),
    ("System under test", "https://github.com/koshakowsky/pokeanalytics"),
]

TECHNIQUE_NAMES = {
    "EP": "Equivalence partitioning",
    "EG": "Error guessing",
    "DT": "Decision tables",
    "ST": "State / sequencing",
    "BVA": "Boundary values",
    "PW": "Pairwise",
    "security": "Security",
    "concurrency": "Concurrency",
    "a11y": "Accessibility",
}

_STATUS_BUCKET = {"passed": "passed", "failed": "failed", "broken": "failed", "skipped": "skipped"}
_SEVERITY_TO_PRIO = {"blocker": "P0", "critical": "P1", "normal": "P2", "minor": "P3"}

CASE_ROW = re.compile(r"^\|\s*((?:TC|E2E)-[A-Z][A-Z0-9]*-\d+[a-z]?)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|")
CASE_ID = re.compile(r"(?:TC|E2E)-[A-Z][A-Z0-9]*-\d+")


# --- Measurement -------------------------------------------------------------

def parse_run(results_dir):
    """Test outcomes and layer split from the Allure results of this run."""
    buckets, prios, layers = Counter(), Counter(), Counter()
    for path in glob.glob(os.path.join(results_dir, "*-result.json")):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        buckets[_STATUS_BUCKET.get(data.get("status"), "other")] += 1
        labels = data.get("labels", [])
        for label in labels:
            if label.get("name") == "severity":
                prios[_SEVERITY_TO_PRIO.get(label["value"], "?")] += 1
        layers[next((l["value"] for l in labels if l["name"] == "parentSuite"), "other")] += 1

    total = sum(buckets.values())
    executed = total - buckets["skipped"]
    return {
        "total": total,
        "passed": buckets["passed"],
        "failed": buckets["failed"],
        "skipped": buckets["skipped"],
        "pass_rate": round(buckets["passed"] / executed * 100, 1) if executed else 0.0,
        "prios": prios,
        "layers": layers,
    }


def parse_catalog():
    """Designed cases per area, and how often each technique is applied.

    Reads the case tables in the catalog, so the numbers move when the catalog
    does - no second list to keep in sync.
    """
    designed = defaultdict(set)
    techniques = Counter()
    for path in sorted(ROOT.glob("test-cases/**/*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = CASE_ROW.match(line)
            if not m:
                continue
            case_id, _title, _prio, technique = m.groups()
            designed[case_id.split("-")[1]].add(case_id)
            if "e2e" in path.parts:
                continue  # the E2E column is a test "kind", not a design technique
            for token in re.split(r"[/,]", technique):
                token = re.sub(r"\(.*?\)|→.*|[·*🐞]|bug-candidate", "", token).strip()
                if token in TECHNIQUE_NAMES:
                    techniques[token] += 1
    return designed, techniques


def parse_automation():
    """Case ids actually referenced by a test."""
    seen = set()
    for pattern in ("api/tests/*.py", "e2e/tests/*.py", "contract/**/*.py", "conftest.py"):
        for path in ROOT.glob(pattern):
            seen |= set(CASE_ID.findall(path.read_text(encoding="utf-8")))
    return seen


def parse_bugs():
    """Each defect with the technique that surfaced it, from the report itself."""
    bugs = []
    for path in sorted(ROOT.glob("bugs/BUG-*.md")):
        text = path.read_text(encoding="utf-8")
        heading = re.search(r"^#\s*(BUG-\d+)\s*[-–—]\s*(.+)$", text, re.M)
        if not heading:
            continue
        status_row = re.search(r"\|\s*\*\*Status\*\*\s*\|\s*\*\*(\w+)", text)
        found_row = re.search(r"\|\s*\*\*Found by\*\*\s*\|\s*(.+?)\s*\|", text)
        found = found_row.group(1) if found_row else ""
        found = re.sub(r"\[.*?\]\(.*?\)|\*\*", "", found)
        if "Contract fuzzing" in found:
            provenance = "contract fuzzing"
        elif "Accessibility" in found:
            provenance = "a11y audit"
        else:
            inner = re.search(r"Test design\s*\(([^)]+)\)", found)
            provenance = inner.group(1).lower() if inner else "test design"
        bugs.append({
            "id": heading.group(1),
            "title": heading.group(2).strip(),
            "status": (status_row.group(1).lower() if status_row else "fixed"),
            "provenance": provenance,
        })
    return bugs


# --- Rendering ---------------------------------------------------------------

def esc(value):
    return html.escape(str(value))


def bar_row(label, done, total, extra=""):
    pct = (done / total * 100) if total else 0
    tone = "good" if done == total else "warn" if pct >= 70 else "bad"
    return (f'<div class="row-bar"><span class="rb-k">{esc(label)}</span>'
            f'<span class="rb-track"><span class="rb-fill {tone}" style="width:{pct:.0f}%"></span></span>'
            f'<span class="rb-n">{done}/{total}</span>{extra}</div>')


def render(run, designed, techniques, automated, bugs):
    build = os.getenv("GITHUB_RUN_NUMBER", "local")
    sha = (os.getenv("GITHUB_SHA", "") or "")[:7]
    when = os.getenv("BUILD_TIME") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    all_designed = {c for ids in designed.values() for c in ids}
    traced = all_designed & automated
    trace_pct = round(len(traced) / len(all_designed) * 100) if all_designed else 0

    area_rows = "".join(
        bar_row(area, len(ids & automated), len(ids))
        for area, ids in sorted(designed.items(), key=lambda kv: -len(kv[1]))
    )

    technique_total = sum(techniques.values()) or 1
    technique_rows = "".join(
        f'<div class="row-bar wide"><span class="rb-k" title="{esc(TECHNIQUE_NAMES[code])}">{esc(code)}</span>'
        f'<span class="rb-track"><span class="rb-fill accent" style="width:{count / technique_total * 100:.0f}%"></span></span>'
        f'<span class="rb-n">{count}</span></div>'
        for code, count in techniques.most_common()
    )

    layer_tiles = "".join(
        f'<div class="tile"><div class="tile-v">{run["layers"].get(name, 0)}</div>'
        f'<div class="tile-l">{esc(name)}</div></div>'
        for name in ("API", "Contract", "E2E")
    )

    prio_rows = "".join(
        f'<div class="row-bar"><span class="rb-k">{p}</span>'
        f'<span class="rb-track"><span class="rb-fill accent" style="width:'
        f'{run["prios"].get(p, 0) / max(run["total"], 1) * 100:.0f}%"></span></span>'
        f'<span class="rb-n">{run["prios"].get(p, 0)}</span></div>'
        for p in ("P0", "P1", "P2", "P3")
    )

    pyramid_rows = "".join(
        f'<div class="row"><span class="row-k">{esc(name)}</span>'
        f'<span class="row-d">{esc(desc)}</span></div>'
        for name, desc in PYRAMID
    )

    bug_rows = "".join(
        f'<div class="bug"><span class="bug-id">{esc(b["id"])}</span>'
        f'<span class="bug-t">{esc(b["title"])}</span>'
        f'<span class="chip sm">{esc(b["provenance"])}</span>'
        f'<span class="pill {"good" if b["status"] == "fixed" else "warn"}">{esc(b["status"])}</span></div>'
        for b in bugs
    )

    chips = "".join(f'<span class="chip">{esc(x)}</span>' for x in STACK)
    links = "".join(f'<a class="lnk" href="{esc(h)}">{esc(t)} →</a>' for t, h in LINKS)
    rate_tone = "good" if run["pass_rate"] >= 100 else "warn" if run["pass_rate"] >= 90 else "bad"

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PokeAnalytics - Test Health</title>
<style>
:root {{
  --bg:#f7f8fa; --surface:#fff; --ink:#0f172a; --ink2:#475569; --muted:#94a3b8;
  --line:#e2e8f0; --good:#16a34a; --warn:#d97706; --bad:#dc2626; --accent:#4f46e5;
  --track:#eef2f7;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#0b1020; --surface:#131a2b; --ink:#e8edf6; --ink2:#9fb0c8;
    --muted:#64748b; --line:#243147; --track:#1c2740; }}
}}
* {{ box-sizing:border-box; min-width:0; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
.wrap {{ max-width:1080px; margin:0 auto; padding:32px 20px 56px; }}
header h1 {{ font-size:24px; margin:0 0 2px; letter-spacing:-.02em; }}
.sub {{ color:var(--ink2); font-size:13px; }}
.meta {{ color:var(--muted); font-size:12px; margin:6px 0 24px; }}
.grid {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); align-items:start; }}
.card {{ background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:18px 20px; }}
.card h2 {{ font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin:0 0 4px; }}
.card .note {{ font-size:12px; color:var(--muted); margin:0 0 14px; }}
.full {{ grid-column:1/-1; }}
.hero {{ display:flex; align-items:baseline; gap:8px; }}
.hero .big {{ font-size:42px; font-weight:800; letter-spacing:-.03em; line-height:1; }}
.hero.good .big {{ color:var(--good); }} .hero.warn .big {{ color:var(--warn); }} .hero.bad .big {{ color:var(--bad); }}
.hero .u {{ color:var(--ink2); font-size:13px; }}
.bar {{ display:flex; height:8px; border-radius:5px; overflow:hidden; margin:14px 0 10px; gap:2px; background:var(--track); }}
.bar i {{ display:block; min-width:3px; }}
.bar .p {{ background:var(--good); }} .bar .s {{ background:var(--warn); }} .bar .f {{ background:var(--bad); }}
.legend {{ display:flex; flex-wrap:wrap; gap:6px 16px; font-size:12px; color:var(--ink2); }}
.legend span {{ white-space:nowrap; }} .legend b {{ color:var(--ink); }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:5px; }}
.tiles {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }}
.tile {{ background:var(--track); border-radius:10px; padding:12px 8px; text-align:center; }}
.tile-v {{ font-size:22px; font-weight:700; line-height:1.1; }}
.tile-l {{ font-size:11px; color:var(--ink2); margin-top:3px; }}
.row-bar {{ display:grid; grid-template-columns:64px 1fr 54px; align-items:center; gap:10px; margin:7px 0; }}
.row-bar.wide {{ grid-template-columns:96px 1fr 44px; }}
.rb-k {{ font-size:12px; font-weight:600; color:var(--ink2); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.rb-track {{ background:var(--track); border-radius:5px; height:8px; overflow:hidden; }}
.rb-fill {{ display:block; height:100%; border-radius:5px; background:var(--accent); }}
.rb-fill.good {{ background:var(--good); }} .rb-fill.warn {{ background:var(--warn); }} .rb-fill.bad {{ background:var(--bad); }}
.rb-n {{ text-align:right; font-variant-numeric:tabular-nums; font-size:12px; color:var(--ink2); }}
.cols2 {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:0 28px; }}
.row {{ display:grid; grid-template-columns:150px 1fr; gap:12px; padding:8px 0; border-top:1px solid var(--line); align-items:baseline; }}
.row:first-of-type {{ border-top:none; }}
.row-k {{ font-weight:600; font-size:13px; }}
.row-d {{ color:var(--ink2); font-size:12px; }}
.bug {{ display:grid; grid-template-columns:74px 1fr auto auto; gap:10px; align-items:center;
  padding:9px 0; border-top:1px solid var(--line); }}
.bug:first-of-type {{ border-top:none; }}
.bug-id {{ font-weight:700; font-size:12px; font-variant-numeric:tabular-nums; }}
.bug-t {{ font-size:13px; color:var(--ink2); }}
.pill {{ font-size:11px; padding:2px 9px; border-radius:999px; font-weight:600; white-space:nowrap; }}
.pill.good {{ color:var(--good); background:color-mix(in srgb,var(--good) 14%,transparent); }}
.pill.warn {{ color:var(--warn); background:color-mix(in srgb,var(--warn) 16%,transparent); }}
.chip {{ display:inline-block; font-size:12px; padding:3px 10px; margin:0 6px 6px 0;
  background:var(--track); border-radius:999px; color:var(--ink2); white-space:nowrap; }}
.chip.sm {{ font-size:11px; padding:2px 8px; margin:0; }}
.links {{ display:flex; flex-wrap:wrap; gap:8px 18px; }}
.lnk {{ color:var(--accent); text-decoration:none; font-size:13px; font-weight:600; }}
.lnk:hover {{ text-decoration:underline; }}
footer {{ margin-top:28px; color:var(--muted); font-size:12px; text-align:center; }}
@media (max-width:560px) {{
  .bug {{ grid-template-columns:1fr auto; }} .bug-t {{ grid-column:1/-1; }}
  .row {{ grid-template-columns:1fr; gap:2px; }}
}}
</style></head><body><div class="wrap">

<header>
  <h1>PokeAnalytics - Test Health</h1>
  <div class="sub">What the run did, and how healthy the test design behind it is.</div>
</header>
<div class="meta">Build #{esc(build)}{(' · ' + sha) if sha else ''} · {esc(when)}</div>

<div class="grid">

  <div class="card">
    <h2>Pass rate</h2>
    <p class="note">This run, across every layer.</p>
    <div class="hero {rate_tone}"><span class="big">{run['pass_rate']:.0f}%</span>
      <span class="u">of {run['total'] - run['skipped']} executed</span></div>
    <div class="bar">
      <i class="p" style="flex:{max(run['passed'], 0)}"></i>
      <i class="s" style="flex:{max(run['skipped'], 0)}"></i>
      <i class="f" style="flex:{max(run['failed'], 0)}"></i>
    </div>
    <div class="legend">
      <span><i class="dot" style="background:var(--good)"></i>Passed <b>{run['passed']}</b></span>
      <span><i class="dot" style="background:var(--warn)"></i>Skipped <b>{run['skipped']}</b></span>
      <span><i class="dot" style="background:var(--bad)"></i>Failed <b>{run['failed']}</b></span>
    </div>
  </div>

  <div class="card">
    <h2>Catalog traceability</h2>
    <p class="note">Designed cases that a named test executes.</p>
    <div class="hero {'good' if trace_pct == 100 else 'warn'}"><span class="big">{trace_pct}%</span>
      <span class="u">{len(traced)} of {len(all_designed)} cases</span></div>
    <p class="note" style="margin:14px 0 0">Verified in CI by
      <code>tools/check_traceability.py --strict</code>, so the claim cannot rot.</p>
  </div>

  <div class="card">
    <h2>Tests by layer</h2>
    <p class="note">Where the run's weight actually sits.</p>
    <div class="tiles">{layer_tiles}</div>
    <p class="note" style="margin:12px 0 0">Contract is one parametrised test that
      fuzzes every documented operation.</p>
  </div>

  <div class="card full">
    <h2>Traceability by area</h2>
    <p class="note">Cases executed vs designed, per catalog area. A gap here means a case
      was written and never automated - the failure mode this dashboard exists to expose.</p>
    <div class="cols2">{area_rows}</div>
  </div>

  <div class="card">
    <h2>Test-design techniques</h2>
    <p class="note">Counted from the catalog's technique column, not declared by hand.
      Cases, not executions: the single pairwise case expands into a generated
      set of combinations at run time.</p>
    {technique_rows}
  </div>

  <div class="card">
    <h2>Executed by priority</h2>
    <p class="note">P0 is the smoke set that gates a release.</p>
    {prio_rows}
  </div>

  <div class="card full">
    <h2>Defects - found, fixed, guarded</h2>
    <p class="note">Every one reached through the same cycle: report → failing test → fix in the
      SUT → the test stays as a regression guard. The chip says which technique surfaced it.</p>
    {bug_rows}
  </div>

  <div class="card full">
    <h2>Test pyramid</h2>
    {pyramid_rows}
  </div>

  <div class="card full">
    <h2>Stack</h2>
    <div>{chips}</div>
  </div>

  <div class="card full">
    <h2>Explore</h2>
    <div class="links">{links}</div>
  </div>

</div>
<footer>Auto-generated by tools/build_dashboard.py on every push to main.</footer>
</div></body></html>
"""


def main():
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "allure-results"
    out = sys.argv[2] if len(sys.argv) > 2 else "index.html"

    run = parse_run(results_dir)
    designed, techniques = parse_catalog()
    automated = parse_automation()
    bugs = parse_bugs()

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(run, designed, techniques, automated, bugs))

    all_designed = {c for ids in designed.values() for c in ids}
    print(f"Wrote {out} - {run['total']} tests ({run['pass_rate']}% pass), "
          f"{len(all_designed & automated)}/{len(all_designed)} cases traced, "
          f"{len(techniques)} techniques, {len(bugs)} defects")


if __name__ == "__main__":
    main()
