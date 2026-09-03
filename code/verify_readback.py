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
caught". PAIRED_FIELD_GROUPS names the fields that must all appear
together or not at all, so that class of gap fails the build instead of
needing a human reviewer to notice a missing denominator.
"""
import re
import os

from render import jval, jtext

SOURCED_RE = re.compile(
    r'<span class="sourced" data-source="([^"]+)"[^>]*>([^<]*)</span>')

# Each group: fields that must ALL be rendered on a page together if ANY
# one of them is, because none of them means anything alone. Paths are
# relative to a line's own results.v1.json.
PAIRED_FIELD_GROUPS = [
    ("paper_sweep.source_items", "paper_sweep.rechecked_by_this_tree",
     "paper_sweep.belongs_to_another_research_line"),
    ("paper_sweep.defects_planted", "paper_sweep.defects_caught_by_the_named_check"),
    ("paper_sweep.controls", "paper_sweep.controls_undisturbed"),
]


class ReadbackFailed(Exception):
    pass


def _resolve(source, path):
    """source is either a single root dict, or {slug: root} for a page
    that can carry more than one line's data. path is 'json.path' or
    '<slug>::json.path'."""
    if "::" in path:
        slug, rest = path.split("::", 1)
        if not isinstance(source, dict) or slug not in source:
            raise KeyError(f"no root registered for line '{slug}'")
        return jval(source[slug], rest), rest, source[slug]
    if isinstance(source, dict) and all(isinstance(v, dict) for v in source.values()) \
            and "global_status" not in source:
        raise KeyError(f"path '{path}' has no line prefix on a multi-line page")
    return jval(source, path), path, source


def verify_page(html_path, source):
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    checked = 0
    rendered_paths_by_root_id = {}
    for m in SOURCED_RE.finditer(content):
        raw_path, rendered = m.group(1), m.group(2)
        try:
            expected_value, bare_path, root = _resolve(source, raw_path)
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
        rendered_paths_by_root_id.setdefault(id(root), set()).add(bare_path)
        checked += 1

    for root_paths in rendered_paths_by_root_id.values():
        for group in PAIRED_FIELD_GROUPS:
            present = [p for p in group if p in root_paths]
            if present and len(present) != len(group):
                missing = [p for p in group if p not in present]
                raise ReadbackFailed(
                    f"{html_path}: rendered {present} without its required pair "
                    f"{missing} -- a number without its denominator is not "
                    f"meaningful on its own")

    return checked
