# AMRAL Verify

Secondary verification of AMRAL research lines. Live at [verify.evemisslab.com](https://verify.evemisslab.com/).

Each line rendered here has its own independent verification arm and its own repository under [amral-research-trees](https://github.com/kakon77777-commits/amral-research-trees) — nothing is vendored into this repo. The build fetches each line's own branch fresh and runs that line's own `validate_results_profiles.py` against it; this repo never hand-parses a research line's data.

## Build

```
python code/build.py
```

Three gates, in order:

1. **Profile check** — fetch each line's branch, run its own `code/validate_results_profiles.py`. A file that declares a profile it doesn't satisfy stops the build.
2. **Render** — every number on the page is wrapped in `sourced()`, carrying the JSON path it came from.
3. **Readback verification** — scrape every built page's numbers back out and re-resolve them against the source JSON. A mismatch stops the build.

Not satisfying the structured-claims profile is not an error — it's a render branch. A line's own stated boundary (`global_status.statement`) is what renders instead, same page, same visibility as a line that does satisfy it.

## Add a line

Append one entry to `code/lines.py`, then rebuild. That file is the only place a line is named.

## Stack

Python generators → static HTML → `wrangler deploy`. No JS runtime dependency, matching [amral.evemisslab.com](https://amral.evemisslab.com/)'s own stack and shared visual system (`public/assets/site.css`, copied verbatim).

## Deploy

```
npx wrangler deploy
```
