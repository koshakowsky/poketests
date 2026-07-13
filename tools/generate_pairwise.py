"""Pairwise generator for TC-LIST-27 (allpairspy).

Regenerates the pairwise table for the list/search filter combinations.
Run and paste the output into test-cases/03-pokemon-list-search.md:

    python tools/generate_pairwise.py

Design decisions (constraints):

* `generation=2` is EXCLUDED from the matrix. With the default seed (Gen I
  only) it always yields an empty result set, on which the verification-bearing
  factors (sort_by / sort_order / limit) cannot be observed. The "valid but
  empty" class is covered by dedicated cases TC-LIST-08/10 instead.
* `types=water` + `is_legendary=true` is excluded via filter: Gen I has no
  water-type legendaries, so the combination is another empty class that would
  waste pair coverage.
"""

from allpairspy import AllPairs

FACTORS = ["types", "generation", "is_legendary", "sort_by", "sort_order", "limit"]

VALUES = [
    [None, "fire", "water"],        # types
    [None, 1],                      # generation
    [None, True, False],            # is_legendary
    ["stat_total", "id"],           # sort_by
    ["asc", "desc"],                # sort_order
    [1, 100],                       # limit
]


def is_valid(partial_row) -> bool:
    """Reject combinations that produce empty result sets (unverifiable sort/limit)."""
    row = dict(zip(FACTORS, partial_row))
    if row.get("types") == "water" and row.get("is_legendary") is True:
        return False  # no water legendaries in Gen I -> empty class
    return True


def fmt(value) -> str:
    if value is None:
        return "—"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def main() -> None:
    rows = list(AllPairs(VALUES, filter_func=is_valid))
    print(f"Generated {len(rows)} rows (all pairs covered, constraints applied)\n")
    print("| # | types | generation | is_legendary | sort_by | sort_order | limit |")
    print("|---|-------|------------|--------------|---------|------------|-------|")
    for i, row in enumerate(rows, 1):
        print("| " + str(i) + " | " + " | ".join(fmt(v) for v in row) + " |")


if __name__ == "__main__":
    main()
