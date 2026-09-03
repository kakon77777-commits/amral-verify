# -*- coding: utf-8 -*-
"""
Gate 2: every rendered number carries the JSON path it came from, as a
data-source attribute -- sourced() is the only way a number should reach
the page. Gate 3 (verify_readback.py) scrapes these back out and diffs
against the original file, so a copy-pasted or hand-typed number that
drifts from its source fails the build, not just looks plausible.
"""
import html
import json
import os

SITE = "https://verify.evemisslab.com/"


def jval(root, path):
    """Resolve a dotted/bracketed path like 'verified_claims.0.claim'
    against a JSON document. Raises KeyError/IndexError if the path is
    wrong -- deliberately not swallowed, since a wrong path here is
    exactly the defect this whole mechanism exists to catch before it
    ships as a page."""
    node = root
    for part in path.split("."):
        node = node[int(part)] if part.isdigit() else node[part]
    return node


def jtext(value):
    """Render a JSON value the same way, whether for the page or for the
    Gate 3 comparison -- these two call sites must never diverge."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def sourced(root, path, line_slug=None):
    """<span> wrapping a value pulled live from root at path, carrying
    its own source path so Gate 3 can check it after the fact.

    line_slug is required on any page that can carry more than one
    line's data (the hub) -- otherwise a bare path is ambiguous about
    which line's JSON it should be checked against. It's encoded into
    data-source as "<slug>::<path>" so verify_readback.py can route each
    span to the right source document."""
    value = jtext(jval(root, path))
    source_attr = f"{line_slug}::{path}" if line_slug else path
    return (f'<span class="sourced" data-source="{html.escape(source_attr)}" '
            f'title="source: {html.escape(path)}">{html.escape(value)}</span>')


def esc(s):
    return html.escape(str(s))


NAV = '''<nav class="sitenav"><div class="inner">
  <a class="brand" href="{r}">AMRAL Verify</a>
  <a class="link" href="{amral}">AMRAL main site</a>
  {here}
</div></nav>'''


def nav(depth, active_href=None, active_label=None):
    r = "../" * depth if depth else "./"
    amral = "https://amral.evemisslab.com/"
    here = f'<a class="link active" href="{active_href}">{active_label}</a>' if active_label else ""
    return NAV.format(r=r, amral=amral, here=here)


PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="robots" content="index, follow">
<link rel="stylesheet" href="{r}assets/site.css">
<link rel="stylesheet" href="{r}assets/verify.css">
</head>
<body>
{nav}
<div class="wrap narrow">
{body}
<footer class="sitefoot">
  <span>AMRAL Verify — secondary verification of AI-frontier-math research lines, rendered from each line's own results.v1.json at build time. A figure with a dotted underline carries the exact source path it was rendered from (hover to see it) — not a link, and results.v1.json is a summary its own build derives from the gate logs, not the gate logs themselves. A number inside a claim's own prose is that claim's own wording, not separately source-tracked.</span>
  <a href="https://amral.evemisslab.com/">AMRAL main site</a>
</footer>
</div>
</body>
</html>'''


def build_hub(lines_data, out_dir):
    cards = []
    for slug, ctx in lines_data.items():
        line = ctx["line"]
        # Full statement text stays in the DOM -- clamped to a few lines
        # visually by CSS (verify.css .card-excerpt), never hard-truncated
        # by character count. A DOM-level cut mid-sentence dropped exactly
        # the half of a non-claim that matters most, found 2026-09-03.
        cards.append(
            f'<a class="case-card" href="{slug}/">'
            f'<span class="k">{esc(line["researcher_label"])}</span>'
            f'<h3>{esc(line["title"])}</h3>'
            f'<p class="card-excerpt">{sourced(ctx["results"], "global_status.statement", line_slug=slug)}</p>'
            f'</a>'
        )
    body = f'''<header class="page">
  <p class="eyebrow">AMRAL VERIFY</p>
  <h1>AMRAL Verify</h1>
  <p class="subtitle">Secondary verification of AMRAL research lines — independent re-derivation, gate logs, and falsifiability drills, rendered from source at build time.</p>
  <p class="lede">Every line here was checked by an arm separate from the one that produced the original research. A line's numbers on this site are never hand-typed: each is rendered from that line's own gate logs, and a build-time check confirms every rendered number still matches its source before the site ships. <strong>A line not satisfying the structured-claims profile is not hidden</strong> — it is rendered from its own stated boundary instead, which is exactly the content a verification site exists to show.</p>
</header>
<section>
  <h2>Research lines</h2>
  <div class="case-grid">
    {"".join(cards)}
  </div>
</section>'''
    html_out = PAGE.format(title="AMRAL Verify", description="Secondary verification of AMRAL research lines, rendered from gate logs at build time.",
                            r="./", nav=nav(0), body=body)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html_out)


def build_status_block(root):
    """global_status.statement, in full, on every line's page regardless
    of which profile it satisfies -- found missing entirely from the
    claims branch 2026-09-03 (the more complete a line's structured data,
    the less of its own boundary statement was showing, which is
    backwards). Same block, same position, both branches."""
    return f'''<section id="status">
  <h2 class="doc-h2">Status</h2>
  <div class="claim-box" style="border-color: var(--ink-dim); background: var(--paper-raised); color: var(--ink);">
    {sourced(root, "global_status.statement")}
  </div>
</section>'''


def build_claims_line(root):
    claims = "".join(
        f'<tr><td class="claim-id">{esc(c.get("id",""))}</td>'
        f'<td>{esc(c.get("claim",""))}</td></tr>'
        for c in root["verified_claims"]
    )
    non_claims = "".join(f"<li>{esc(s)}</li>" for s in root["explicit_non_claims"])
    return build_status_block(root) + f'''
<section id="claims">
  <h2 class="doc-h2">Verified claims</h2>
  <table class="ledger"><thead><tr><th>ID</th><th>Claim</th></tr></thead><tbody>{claims}</tbody></table>
</section>
<section id="non-claims">
  <h2 class="doc-h2">Explicit non-claims</h2>
  <p class="section-note">What this line does not establish, stated by the line itself — rendered on the same screen as the claims above, not behind a toggle.</p>
  <ul class="non-claims">{non_claims}</ul>
</section>'''


def build_envelope_only_line(root):
    return build_status_block(root) + '''
<section id="claims">
  <p class="section-note">This line does not yet satisfy the structured-claims profile (<code>results-claims/1</code>) — it has no <code>verified_claims</code>/<code>explicit_non_claims</code> arrays. That is not an error: its boundary is stated above in its own words, and is rendered here rather than dropped because it did not arrive in the expected fields.</p>
</section>'''


def build_line_detail(line, ctx, out_dir):
    root = ctx["results"]
    ev = ctx["evaluation"]
    slug = line["slug"]
    satisfies_claims = "results-claims/1" in ev["satisfies"]

    body_claims = build_claims_line(root) if satisfies_claims else build_envelope_only_line(root)

    # Standalone figures worth headlining are this line's own declaration
    # (headline_figures, under results-figures/1) -- never a hardcoded
    # path list here. This is what let Collatz-specific field names
    # (paper_sweep.run_reports etc.) leak into a renderer meant to work
    # for any line's own data shape; a line's own validator enforces that
    # nothing declared here also appears in its own render_pairs, so a
    # figure that needs a denominator can't be re-offered as if it didn't.
    # kind distinguishes a single value ("number", default) from a
    # two-endpoint range ("range", e.g. a covered domain) that must
    # render as one figure, not two separately-droppable numbers -- a
    # range declared as two independent figures would let this renderer
    # show the lower bound without the upper one, the same "denominator
    # went missing" shape as an unpaired figure, just wearing a range's
    # clothes. The declared kind is cross-checked against the actual
    # parsed shape by the line's own validator, not trusted blindly here.
    stat_html = "".join(build_headline_figure(root, f) for f in ev.get("headline_figures_to_render", [])
                         if _path_exists(root, f.get("path", "")))

    # Which figures must never render alone is this line's own fact, not
    # something this renderer can guess -- read from the line's own
    # validator output (figures_that_must_not_be_shown_alone under the
    # results-pairs/1 profile), never hand-typed here. A new pair the
    # source declares appears with no change on this end; one this
    # renderer can't resolve is simply skipped, not guessed at.
    scale_html = build_pairs_section(root, ev.get("figures_that_must_not_be_shown_alone", []))

    gate_rows = []
    for gname, gpath in [("Self-test", "gates.self_test.ok"),
                          ("Reference cross-check", "gates.reference_cross_check.agree"),
                          ("External anchors (OEIS)", "gates.external_anchors.ok"),
                          ("Mutation drill", "gates.mutation_drill.ok")]:
        if _path_exists(root, gpath):
            gate_rows.append(f'<tr><td>{esc(gname)}</td><td>{sourced(root, gpath)}</td></tr>')
    gates_html = f'<table class="ledger"><thead><tr><th>Gate</th><th>Result</th></tr></thead><tbody>{"".join(gate_rows)}</tbody></table>' if gate_rows else ""

    # No hardcoded Coverage section left at all -- the domain range that
    # used to live here is now declared as a "range"-kind headline figure
    # (coverage.covered_interval) and rendered generically above, with a
    # source path it didn't reliably carry as a matter of contract before
    # (only as a matter of how this renderer happened to be written).

    # A heading with nothing under it reads as "this line has none of
    # this" or "this page is broken", not "this line's own data uses a
    # different shape" -- found on the ERDOS page 2026-09-03, where
    # paper_sweep/gates are Collatz's own field names and don't exist in
    # ERDOS's (exact_reduction/exact_certificates/bounded_searches). Omit
    # the section (heading included) entirely rather than ship an empty
    # one; this renderer has no generic way yet to say why it's empty for
    # a line whose evidence shape it doesn't recognize.
    scale_section = (f'<section>\n  <h2 class="doc-h2">Verification scale</h2>\n'
                      f'  {scale_html}\n  <div class="stats">{stat_html}</div>\n</section>'
                      if (scale_html or stat_html) else "")
    gates_section = (f'<section id="gates">\n  <h2 class="doc-h2">Gates</h2>\n'
                      f'  {gates_html}\n</section>'
                      if gates_html else "")

    body = f'''<div class="crumb"><a href="../">← AMRAL Verify</a> · {esc(slug)}</div>
<header class="pkg">
  <div class="idline">
    <span class="tag">{esc(line["researcher_label"])}</span>
    <span class="status">{esc(root["date"])}</span>
  </div>
  <h1>{esc(line["title"])}</h1>
  <p class="h1-sub">Profile: {esc(", ".join(ev["satisfies"]) or "envelope not satisfied")}</p>
</header>
{body_claims}
{scale_section}
{gates_section}
<section id="provenance">
  <h2 class="doc-h2">Provenance</h2>
  <p class="section-note">Rendered {esc(_today())} from <code>{esc(line["branch"])}</code> at build time — not vendored into this site. Full reports and gate logs: <a href="https://github.com/kakon77777-commits/amral-research-trees/tree/{esc(line["branch"])}/{esc(slug)}">amral-research-trees / {esc(line["branch"])}</a>.</p>
</section>'''

    out = os.path.join(out_dir, slug)
    os.makedirs(out, exist_ok=True)
    html_out = PAGE.format(
        title=f'{line["title"]} · AMRAL Verify',
        description=esc(root["global_status"]["statement"]),
        r="../", nav=nav(1, "./", line["title"]), body=body)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html_out)


def build_headline_figure(root, f):
    """One <div class="stat"> for a declared headline figure. kind
    "number" (default) sources a single value; "range" sources the two
    elements of a list value and shows them together, since a range's two
    endpoints are one figure, not two independently-droppable ones -- the
    line's own validator cross-checks the declared kind against what the
    path actually resolves to, so an inconsistent declaration never
    reaches this function at all."""
    kind = f.get("kind", "number")
    label = esc(f.get("label", ""))
    if kind == "range":
        lo, hi = f["path"] + ".0", f["path"] + ".1"
        return f'<div class="stat"><span class="n">{sourced(root, lo)} – {sourced(root, hi)}</span><span class="l">{label}</span></div>'
    return f'<div class="stat"><span class="n">{sourced(root, f["path"])}</span><span class="l">{label}</span></div>'


def build_pairs_section(root, pairs):
    """Render every figure the line's own validator declares must not be
    shown alone -- generically, from figures_that_must_not_be_shown_alone,
    never a list hand-typed on this end. That list is the line's own
    semantic fact (which number is load-bearing), and hand-copying it
    here would just be a second copy of the same truth this whole day's
    work has been about eliminating. A pair this renderer can't resolve
    (a path that doesn't exist in this build) is skipped, not guessed at."""
    if not pairs:
        return ""
    rows = []
    for p in pairs:
        if not (_path_exists(root, p.get("value", "")) and _path_exists(root, p.get("against", ""))):
            continue
        rows.append(
            f'<tr><td>{sourced(root, p["value"])} / {sourced(root, p["against"])}</td>'
            f'<td>{esc(p.get("label", ""))}</td></tr>'
        )
    if not rows:
        return ""
    return (f'<table class="ledger"><thead><tr><th>Figure / against</th><th>What it measures</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def _path_exists(root, path):
    try:
        jval(root, path)
        return True
    except (KeyError, IndexError, TypeError):
        return False


def _today():
    import datetime
    return datetime.date.today().isoformat()
