"""Score the section choice against tests/filing_cases.tsv.

    uv run python -m lifekit.library.filing_test

Each row holds a question and the section a reader expects. The script asks the
model to choose a section for each question the way online retrieval does and
prints the share it gets right and every miss. A change to the prompt stays
only when the share rises.
"""

import csv
from pathlib import Path

from . import provider
from .online_retrieval import SECTION_PROMPT, choose_section
from .verdicts import filing_examples

CASES = Path(__file__).resolve().parents[2] / "tests" / "filing_cases.tsv"


def main() -> None:
    with CASES.open(newline="") as handle:
        cases = list(csv.DictReader(handle, delimiter="\t"))
    examples = "".join(f"\nExample: {q} -> {s}" for q, s in filing_examples())
    right = 0
    for case in cases:
        chosen = choose_section(provider.ask, SECTION_PROMPT + examples, case["question"], case["question"])
        ok = chosen == case["section"]
        right += ok
        if not ok:
            print(f"miss  {case['question']!r}: chose {chosen}, expected {case['section']}")
    print(f"{right}/{len(cases)} right ({100 * right // len(cases)} percent)")


if __name__ == "__main__":
    main()
