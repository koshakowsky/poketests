import argparse
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent

SUITES = {
    "API": {
        "pattern": re.compile(r"TC-[A-Z]+-\d+"),
        "catalog": ["test-cases/api/*.md"],
        "tests": ["api/tests/*.py", "contract/**/*.py", "conftest.py"],
    },
    "E2E": {
        "pattern": re.compile(r"E2E-[A-Z][A-Z0-9]*-\d+"),
        "catalog": ["test-cases/e2e/*.md"],
        "tests": ["e2e/tests/*.py"],
    },
}


def _ids(globs: list[str], pattern: re.Pattern) -> set[str]:
    found: set[str] = set()
    for spec in globs:
        for path in ROOT.glob(spec):
            found |= set(pattern.findall(path.read_text(encoding="utf-8")))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="exit 1 on any gap")
    args = parser.parse_args()

    failed = False
    for suite, cfg in SUITES.items():
        designed = _ids(cfg["catalog"], cfg["pattern"])
        automated = _ids(cfg["tests"], cfg["pattern"])
        traced = designed & automated
        missing = sorted(designed - automated)
        orphans = sorted(automated - designed)

        pct = len(traced) * 100 // len(designed) if designed else 0
        print(f"{suite}: {len(traced)}/{len(designed)} traced ({pct}%)")

        if missing:
            failed = True
            by_area = Counter(i.split("-")[1] for i in missing)
            print(f"  designed but NOT automated ({len(missing)}): {', '.join(missing)}")
            print(f"  by area: {dict(by_area)}")
        if orphans:
            failed = True
            print(f"  referenced in tests but NOT in the catalog: {', '.join(orphans)}")

    if failed and args.strict:
        print("\nTraceability gaps found.", file=sys.stderr)
        return 1
    if not failed:
        print("\nEvery designed case is executed by a test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
