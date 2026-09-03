# -*- coding: utf-8 -*-
"""
Gate 3: after a line's page is built, scrape every sourced() span back out
of the actual HTML on disk and re-resolve its data-source path against the
original results.v1.json. A mismatch fails the build.

This is deliberately independent of render.py's own bookkeeping -- it
reads the FILE that was written, not the strings render.py thinks it
wrote, so a bug in render.py itself (e.g. writing to the wrong path, or a
template placeholder silently not substituting) is still caught.

Checks fidelity (does a rendered value match its source) AND sufficiency
(is a value's necessary pair also rendered) -- fidelity alone missed a
real defect on 2026-09-03: "1441 defects caught" was correct and,
unpaired with "1441 planted", indistinguishable from "1441 of 2000
caught". Which figures must not stand alone is each line's OWN fact
(figures_that_must_not_be_shown_alone, under the results-pairs/1
profile) -- never a list hand-typed on this end, which would just be a
second, driftable copy of that line's own semantics.
"""
import re

from render import jval, jtext

SOURCED_RE = re.compile(
    r'<span class="sourced" data-source="([^"]+)"[^>]*>([^<]*)</span>')


class ReadbackFailed(Exception):
    pass


def _resolve(source, path):
    """source is either a single root dict (key None), or {slug: root}
    for a page that can carry more than one line's data. path is
    'json.path' or '<slug>::json.path'. Returns (value, bare_path, key)
    where key identifies which root/pairs-list this span belongs to."""
    if "::" in path:
        slug, rest = path.split("::", 1)
        if not isinstance(source, dict) or slug not in source:
            raise KeyError(f"no root registered for line '{slug}'")
        return jval(source[slug], rest), rest, slug
    if isinstance(source, dict) and all(isinstance(v, dict) for v in source.values()) \
            and "global_status" not in source:
        raise KeyError(f"path '{path}' has no line prefix on a multi-line page")
    return jval(source, path), path, None


def verify_page(html_path, source, pairs=None):
    """pairs is either a flat list of {value, against} dicts (source is a
    single root) or {slug: [pairs...]} (source is {slug: root})."""
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    checked = 0
    rendered_paths_by_key = {}
    for m in SOURCED_RE.finditer(content):
        raw_path, rendered = m.group(1), m.group(2)
        try:
            expected_value, bare_path, key = _resolve(source, raw_path)
            expected = jtext(expected_value)
        except (KeyError, IndexError, TypeError) as exc:
            raise ReadbackFailed(
                f"{html_path}: data-source=\"{raw_path}\" no longer resolves against "
                f"the source JSON ({exc})")
        rendered_unescaped = (rendered.replace("&amp;", "&").replace("&lt;", "<")
                              .replace("&gt;", ">").replace("&quot;", '"')
                              .replace("&#x27;", "'"))
        if rendered_unescaped != expected:
            raise ReadbackFailed(
                f"{html_path}: data-source=\"{raw_path}\" rendered "
                f"\"{rendered_unescaped}\" but source is \"{expected}\"")
        rendered_paths_by_key.setdefault(key, set()).add(bare_path)
        checked += 1

    for key, rendered_paths in rendered_paths_by_key.items():
        key_pairs = (pairs.get(key, []) if isinstance(pairs, dict) else (pairs or []))
        for p in key_pairs:
            value_path, against_path = p.get("value"), p.get("against")
            if not value_path or not against_path:
                continue
            has_value = value_path in rendered_paths
            has_against = against_path in rendered_paths
            if has_value != has_against:
                shown, missing = (value_path, against_path) if has_value else (against_path, value_path)
                raise ReadbackFailed(
                    f"{html_path}: rendered \"{shown}\" without its required pair "
                    f"\"{missing}\" ({p.get('label', 'no label')}) -- a number without "
                    f"its denominator is not meaningful on its own")

    return checked
