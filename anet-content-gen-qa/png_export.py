"""
png_export.py
==============
Optional SVG -> PNG conversion for the exit ticket pipeline.

The original ETGenerator tool never did this — it shipped SVG only (inline in
the HTML, and as standalone .svg files), because SVG renders natively in any
browser and needs zero extra dependencies. That's still the primary format
here for exactly that reason.

PNG export is offered on top as a convenience (some downstream tools — Word,
older LMS uploaders, email clients — don't handle inline SVG well). It relies
on `cairosvg`, which needs the system Cairo graphics library to actually
render at runtime, even though the Python package installs fine everywhere.
That runtime dependency is NOT guaranteed on a fresh Mac, so this module is
deliberately best-effort: every call is wrapped so a missing/broken Cairo
install degrades to "PNG unavailable" rather than crashing the app or
blocking setup. SVG output is never blocked by a PNG failure.

If you want PNG export and don't have it: `brew install cairo` (Mac) or
`apt install libcairo2` (Linux), then restart the app. No action needed on
Windows — cairosvg's Windows wheels bundle what they need.
"""

from __future__ import annotations

import io

_CAIROSVG_ERROR: str | None = None
try:
    import cairosvg  # type: ignore
except Exception as e:  # ImportError, OSError (missing libcairo), etc.
    cairosvg = None  # type: ignore
    _CAIROSVG_ERROR = str(e)


def png_available() -> bool:
    """True if this environment can actually rasterize SVG -> PNG right now."""
    return cairosvg is not None


def png_unavailable_reason() -> str:
    """Human-readable reason PNG export isn't available, for the UI to show once."""
    if png_available():
        return ""
    return (
        "PNG export needs the Cairo graphics library, which isn't available here. "
        "SVG visuals still work everywhere (Streamlit preview, the HTML report, "
        "and most modern apps). To enable PNG too: run `brew install cairo` "
        "(Mac) or `apt install libcairo2` (Linux), then restart the app."
        + (f"\n\nDetail: {_CAIROSVG_ERROR}" if _CAIROSVG_ERROR else "")
    )


def svg_to_png_bytes(svg_string: str, scale: float = 2.0) -> bytes | None:
    """
    Convert an SVG string to PNG bytes at `scale`x the SVG's declared size
    (2x by default, matching the crispness of the original tool's raster
    exports). Returns None if Cairo isn't available — callers should check
    png_available() first if they want to warn the user once up front rather
    than getting None back silently for every image.
    """
    if not png_available():
        return None
    try:
        buf = io.BytesIO()
        cairosvg.svg2png(bytestring=svg_string.encode("utf-8"),
                          write_to=buf, scale=scale)
        return buf.getvalue()
    except Exception:
        # A single malformed visual shouldn't take down the whole export —
        # the SVG is still saved regardless of what happens here.
        return None
