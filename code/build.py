# -*- coding: utf-8 -*-
"""
Build orchestrator, all three gates in order:

  1. fetch_and_validate_all -- clone amral-research-trees fresh (once),
     run validate_results_profiles.py in its own cross-branch mode. A
     registered line that declares a profile it doesn't satisfy stops
     the build here.
  2. render -- build the site, every number wrapped in sourced() so it
     carries the JSON path it came from.
  3. verify_readback -- scrape every built page's sourced() spans back out
     and re-resolve them against the original JSON. A mismatch stops the
     build here, after generation, independent of render.py's own logic.

Usage: python code/build.py
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lines as lines_module
import fetch_and_validate as gate1
import render as gate2
import verify_readback as gate3

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(REPO, "public")


def main():
    cache_dir = tempfile.mkdtemp(prefix="amral-verify-build-")
    try:
        print(f"Gate 1: fetch + profile-check {len(lines_module.LINES)} line(s)")
        lines_data = gate1.fetch_and_validate_all(lines_module.LINES, cache_dir)
        for slug, ctx in lines_data.items():
            print(f"  {slug} <- {ctx['line']['branch']}")
            print(f"    satisfies: {ctx['evaluation']['satisfies'] or '(envelope only)'}")

        print("Gate 2: render")
        gate2.build_hub(lines_data, PUBLIC)
        for slug, ctx in lines_data.items():
            gate2.build_line_detail(ctx["line"], ctx, PUBLIC)
        print(f"  wrote {len(lines_data) + 1} page(s) to {PUBLIC}")

        print("Gate 3: readback verification")
        total_checked = 0
        hub_roots = {slug: ctx["results"] for slug, ctx in lines_data.items()}
        hub_pairs = {slug: ctx["evaluation"].get("figures_that_must_not_be_shown_alone", [])
                     for slug, ctx in lines_data.items()}
        n = gate3.verify_page(os.path.join(PUBLIC, "index.html"), hub_roots, hub_pairs)
        print(f"  hub: {n} sourced values, all match their source")
        total_checked += n
        for slug, ctx in lines_data.items():
            page = os.path.join(PUBLIC, slug, "index.html")
            pairs = ctx["evaluation"].get("figures_that_must_not_be_shown_alone", [])
            n = gate3.verify_page(page, ctx["results"], pairs)
            print(f"  {slug}: {n} sourced values, all match their source"
                  f"{f', {len(pairs)} declared pair(s) enforced' if pairs else ''}")
            total_checked += n
        print(f"  {total_checked} sourced values verified across all pages")

        print("BUILD OK")
        return 0
    except (gate1.ProfileCheckFailed, gate3.ReadbackFailed) as exc:
        print(f"BUILD FAILED: {exc}")
        return 1
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
