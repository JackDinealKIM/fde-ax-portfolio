#!/usr/bin/env python3
"""Build documents/fde-portfolio-demo/index.html — a single self-contained file.

The template (src/index.template.html) carries a /*THREE_INLINE*/ marker inside a
<script> tag. This script replaces that marker with the local three.js build so the
demo works with zero network access (GitHub Pages, offline laptops, closed networks).

Usage:  python3 build.py
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE / "src" / "index.template.html"
THREE = pathlib.Path("/workspace/deploy/guri-3d-calendar/vendor/three.min.js")
OUT = HERE / "index.html"
MARKER = "/*THREE_INLINE*/"


def main() -> int:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    if MARKER not in tpl:
        print(f"marker {MARKER!r} not found in template", file=sys.stderr)
        return 1
    three = THREE.read_text(encoding="utf-8")
    if "</script" in three:
        print("three.min.js contains a closing script tag; cannot inline safely", file=sys.stderr)
        return 1
    html = tpl.replace(MARKER, "\n" + three + "\n", 1)
    OUT.write_text(html, encoding="utf-8")
    size = OUT.stat().st_size
    print(f"built {OUT} ({size:,} bytes, three.js inlined)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
