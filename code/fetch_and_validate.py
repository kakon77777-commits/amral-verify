# -*- coding: utf-8 -*-
"""
Gate 1: fetch a research line's branch fresh (never vendored into this
repo) and run ITS OWN validate_results_profiles.py against ITS OWN
results.v*.json -- never hand-parse the JSON's schema_version, since that
integer doesn't identify structure (see collatz-verification-zhuiheng's
reports/RESULTS-PROFILES.md). A file that declares a profile it does not
satisfy fails the build; this is the only hard failure at this gate.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

from lines import RESEARCH_TREES_REMOTE


class ProfileCheckFailed(Exception):
    pass


def _run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    return r


def fetch_line(line, cache_dir):
    """Shallow single-branch clone into cache_dir/<slug>. Returns the path
    to that line's own subdirectory inside the clone (the monorepo keeps
    one top-level directory per line even on a line's own branch)."""
    slug = line["slug"]
    dest = os.path.join(cache_dir, slug)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    r = _run(["git", "clone", "--depth", "1", "--branch", line["branch"],
              "--single-branch", RESEARCH_TREES_REMOTE, dest], cwd=cache_dir)
    if r.returncode != 0:
        raise ProfileCheckFailed(f"clone failed for {slug}: {r.stderr}")
    line_dir = os.path.join(dest, slug)
    if not os.path.isdir(line_dir):
        raise ProfileCheckFailed(
            f"expected {slug}/ inside the clone of {line['branch']}, not found")
    return line_dir


def check_profile(line, line_dir):
    """Run the line's own validator against its own results file. Returns
    the parsed evaluation dict. Raises ProfileCheckFailed on a lying file
    or a validator that can't be run at all -- both stop the build."""
    validator = os.path.join(line_dir, "code", "validate_results_profiles.py")
    results_path = os.path.join(line_dir, "data", "results.v1.json")
    if not os.path.isfile(validator):
        raise ProfileCheckFailed(f"{line['slug']}: no validate_results_profiles.py in its own code/")
    if not os.path.isfile(results_path):
        raise ProfileCheckFailed(f"{line['slug']}: no data/results.v1.json")

    r = _run([sys.executable, validator, "--paths",
               os.path.relpath(results_path, line_dir)], cwd=line_dir)
    # the validator's own exit code is 0 unless a file LIES about a profile
    # it declares -- that is the one condition this build must not paper over
    if r.returncode != 0:
        raise ProfileCheckFailed(
            f"{line['slug']}: validate_results_profiles.py exited {r.returncode} "
            f"(a declared profile was not satisfied)\n{r.stdout}\n{r.stderr}")

    log_path = os.path.join(line_dir, "data", "gate-logs", "results-profiles.json")
    with open(log_path, encoding="utf-8") as f:
        log = json.load(f)
    matches = [row for row in log["files"]
               if row.get("research_line_id") == line["slug"]]
    if not matches:
        raise ProfileCheckFailed(
            f"{line['slug']}: its own validator's log doesn't mention it")
    return matches[0]


def fetch_and_validate(line, cache_dir):
    line_dir = fetch_line(line, cache_dir)
    evaluation = check_profile(line, line_dir)
    with open(os.path.join(line_dir, "data", "results.v1.json"), encoding="utf-8") as f:
        results = json.load(f)
    return {"line_dir": line_dir, "evaluation": evaluation, "results": results}
