# -*- coding: utf-8 -*-
"""
The one list of which research lines this sub-site renders, and where
their source lives. This is the case-list-as-ground-truth AMRAL's own
nav module (amral/tools/nav/amral_nav.py) uses for the same reason: one
list, not a copy of it per page.

To add a line: append one entry here, run `python code/build.py`. Nothing
else changes. A line's branch is fetched fresh at build time (never
vendored into this repo) and validate_results_profiles.py -- which only
lives on VALIDATOR_BRANCH today -- is what decides how each registered
line renders. Its own discover() reads every branch's results.v*.json via
`git show`, so it does not need to be copied onto every line's own
branch; only the line that first wrote it (collatz-verification-zhuiheng)
carries it. Found 2026-09-03 when erdos-885-k5-chengxu was added and its
own branch had no copy of the script at all.
"""

RESEARCH_TREES_REMOTE = "https://github.com/kakon77777-commits/amral-research-trees.git"

# validate_results_profiles.py's home -- run from here, in its default
# (no --paths) mode, so its own cross-branch discover() finds every
# registered line's results.v1.json, not just this branch's own.
VALIDATOR_BRANCH = "agent/collatz-verification-zhuiheng"
VALIDATOR_RELPATH = "collatz-verification-zhuiheng/code/validate_results_profiles.py"
VALIDATOR_LOG_RELPATH = "collatz-verification-zhuiheng/data/gate-logs/results-profiles.json"

LINES = [
    {
        "slug": "collatz-verification-zhuiheng",
        "branch": "agent/collatz-verification-zhuiheng",
        "title": "Collatz Conjecture — Secondary Verification",
        "title_zh": "考拉茲猜想 · 二次驗證",
        "researcher_label": "數學戰士「墜衡」",
    },
    {
        "slug": "erdos-885-k5-chengxu",
        "branch": "agent/archive-chengxu-erdos-885-k5",
        "title": "Erdős 885 (k=5) — Secondary Verification",
        "title_zh": "Erdős 885（k=5）· 二次驗證",
        "researcher_label": "澄序",
    },
]
