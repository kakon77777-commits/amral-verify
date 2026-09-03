# -*- coding: utf-8 -*-
"""
Gate 1: fetch amral-research-trees fresh (never vendored into this repo)
and run validate_results_profiles.py -- in its own default, no-argument
mode, which discovers every results.v*.json across every branch itself
via `git show`, not a checkout per line -- so a second line needs no copy
of the script on its own branch. Never hand-parse schema_version, which
doesn't identify structure across lines (see
collatz-verification-zhuiheng/reports/RESULTS-PROFILES.md).

A line that DECLARES a profile it doesn't satisfy stops the build. This
is checked per registered line, not on the validator's own overall exit
code -- an unrelated line elsewhere in the monorepo failing its own
checks is not this site's problem to fail its build over.
"""
import json
import os
import subprocess
import sys

from lines import (RESEARCH_TREES_REMOTE, VALIDATOR_BRANCH,
                    VALIDATOR_RELPATH, VALIDATOR_LOG_RELPATH)


class ProfileCheckFailed(Exception):
    pass


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")


def clone_repo(cache_dir):
    """One full clone (every branch), reused for both the validator run
    and reading each line's own data via `git show` -- no per-line
    checkout needed."""
    dest = os.path.join(cache_dir, "amral-research-trees")
    r = _run(["git", "clone", RESEARCH_TREES_REMOTE, dest], cwd=cache_dir)
    if r.returncode != 0:
        raise ProfileCheckFailed(f"clone of amral-research-trees failed: {r.stderr}")
    return dest


def run_validator(repo_dir):
    """Checkout the one branch that carries validate_results_profiles.py
    and run it with no arguments -- its own discover() finds every
    results.v*.json across every branch from there. Returns the full
    parsed results-profiles.json log."""
    r = _run(["git", "checkout", VALIDATOR_BRANCH], cwd=repo_dir)
    if r.returncode != 0:
        raise ProfileCheckFailed(f"checkout of {VALIDATOR_BRANCH} failed: {r.stderr}")
    validator_path = os.path.join(repo_dir, VALIDATOR_RELPATH)
    if not os.path.isfile(validator_path):
        raise ProfileCheckFailed(f"{VALIDATOR_RELPATH} not found on {VALIDATOR_BRANCH}")
    validator_dir = os.path.dirname(validator_path)
    r = _run([sys.executable, os.path.basename(validator_path)], cwd=validator_dir)
    # Deliberately not checking r.returncode here -- the validator's own
    # exit code reflects EVERY results file in the whole monorepo, not
    # just the lines this site registers. A line this site never renders
    # failing its own checks is not grounds to fail this build.
    log_path = os.path.join(repo_dir, VALIDATOR_LOG_RELPATH)
    if not os.path.isfile(log_path):
        raise ProfileCheckFailed(
            f"validator ran but wrote no log at {VALIDATOR_LOG_RELPATH}\n{r.stdout}\n{r.stderr}")
    with open(log_path, encoding="utf-8") as f:
        return json.load(f)


def read_json_from_branch(repo_dir, branch, path):
    r = _run(["git", "show", f"origin/{branch}:{path}"], cwd=repo_dir)
    if r.returncode != 0:
        raise ProfileCheckFailed(f"couldn't read {path} from {branch}: {r.stderr}")
    return json.loads(r.stdout)


def fetch_and_validate_all(lines, cache_dir):
    """Returns {slug: {"line":..., "evaluation":..., "results":...}} for
    every registered line, having run the profile check on all of them
    from one clone and one validator invocation."""
    repo_dir = clone_repo(cache_dir)
    log = run_validator(repo_dir)
    by_line_id = {row.get("research_line_id"): row
                  for row in log.get("files", []) if "research_line_id" in row}

    out = {}
    for line in lines:
        slug = line["slug"]
        evaluation = by_line_id.get(slug)
        if evaluation is None:
            raise ProfileCheckFailed(
                f"{slug}: not found in the validator's cross-branch scan "
                f"(checked {len(by_line_id)} file(s))")
        lying = evaluation.get("declared_but_not_satisfied")
        if lying:
            raise ProfileCheckFailed(
                f"{slug}: declares {lying} in its own results.v1.json without satisfying them")
        # render.py's templates read global_status.statement, .date, etc.
        # unconditionally -- every registered line must satisfy at least
        # the envelope, or those reads crash deep inside rendering
        # instead of failing clearly here. Found by proactively testing
        # the envelope-only branch with an incomplete synthetic document
        # 2026-09-03 -- a real gap, not just an incomplete test: nothing
        # upstream of render.py had ever enforced this.
        if "results-envelope/1" not in evaluation.get("satisfies", []):
            raise ProfileCheckFailed(
                f"{slug}: does not satisfy results-envelope/1 -- gaps: "
                f"{evaluation.get('gaps', {}).get('results-envelope/1', 'unknown')}")
        data_path = f"{slug}/data/results.v1.json"
        results = read_json_from_branch(repo_dir, line["branch"], data_path)
        out[slug] = {"line": line, "evaluation": evaluation, "results": results}
    return out
