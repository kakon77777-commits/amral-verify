# -*- coding: utf-8 -*-
"""
The one list of which research lines this sub-site renders, and where
their source lives. This is the case-list-as-ground-truth AMRAL's own
nav module (amral/tools/nav/amral_nav.py) uses for the same reason: one
list, not a copy of it per page.

To add a line: append one entry here, run `python code/build.py`. Nothing
else changes. The line's own branch is fetched fresh at build time
(never vendored into this repo) and its own validate_results_profiles.py
is what decides how it renders -- this file only says WHERE to look.
"""

RESEARCH_TREES_REMOTE = "https://github.com/kakon77777-commits/amral-research-trees.git"

LINES = [
    {
        "slug": "collatz-verification-zhuiheng",
        "branch": "agent/collatz-verification-zhuiheng",
        "title": "Collatz Conjecture — Secondary Verification",
        "title_zh": "考拉茲猜想 · 二次驗證",
        "researcher_label": "數學戰士「墜衡」",
    },
]
