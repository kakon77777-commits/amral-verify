# -*- coding: utf-8 -*-
"""
Gate 3: after a line's page is built, scrape every sourced() span back out
of the actual HTML on disk and re-resolve its data-source path against the
original results.v1.json. A mismatch fails the build.

This is deliberately independent of render.py's own bookkeeping -- it
reads the FILE that was written, not the strings render.py thinks it
wrote, so a bug in render.py itself (e.g. writing to the wrong path, or a
template placeholder silently not substituting) is still caught.
"""
import re
import os

from render import jval, jtext

SOURCED_RE = re.compile(
    r'<span class="sourced" data-source="([^"]+)"[^>]*>([^<]*)</span>')


class ReadbackFailed(Exception):
    pass


def verify_page(html_path, root):
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    checked = 0
    for m in SOURCED_RE.finditer(content):
        path, rendered = m.group(1), m.group(2)
        try:
            expected = jtext(jval(root, path))
        except (KeyError, IndexError, TypeError) as exc:
            raise ReadbackFailed(
                f"{html_path}: data-source=\"{path}\" no longer resolves against "
                f"the source JSON ({exc})")
        # HTML-unescape the minimal set sourced() actually escapes
        rendered_unescaped = (rendered.replace("&amp;", "&").replace("&lt;", "<")
                              .replace("&gt;", ">").replace("&quot;", '"')
                              .replace("&#x27;", "'"))
        if rendered_unescaped != expected:
            raise ReadbackFailed(
                f"{html_path}: data-source=\"{path}\" rendered "
                f"\"{rendered_unescaped}\" but source is \"{expected}\"")
        checked += 1
    return checked
