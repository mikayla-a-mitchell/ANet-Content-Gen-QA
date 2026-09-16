"""
visual_renderers.py
===================
Python rendering database for the Exit Ticket Pipeline.

Every renderer:
  - Accepts a spec dict parsed from the <VISUAL_SPEC> XML element in Phase 2 output
  - Computes ALL pixel coordinates mathematically — no estimation, no guessing
  - Returns a complete <svg>...</svg> string (no CDATA; the pipeline wraps it)
  - Raises ValueError with a clear message if required spec fields are missing

Call render_visual(spec_dict) to dispatch.
Returns (svg_string, "database") on success.
Returns (None, "fallback") if the type key is not registered.
Unknown types are also written to unknown_visuals.log by the pipeline.

Registered types (30):
  Number lines:      number_line_h, number_line_h_arrow, number_line_inequality,
                     number_line_v, double_number_line
  Fraction models:   fraction_strip, tape_diagram, area_model_fraction,
                     area_model_multiplication
  Arrays:            array
  Geometry 2D:       rectangle, parallelogram, triangle, circle, right_triangle
  Coordinate plane:  coordinate_q1, coordinate_4q, linear_graph, slope_triangle
  Data displays:     bar_graph, dot_plot, histogram, box_plot, box_plot_comparative,
                     circle_graph, scatter_plot, two_way_table
  Measurement:       place_value_chart, rectangular_prism_labeled
  3D:                unit_cube_isometric
"""

import math
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# STYLE CONSTANTS  (all visuals use black / white / gray only)
# ═══════════════════════════════════════════════════════════════════════════════

FONT        = "Lato, Arial, sans-serif"
FS          = 14          # standard font size (px)
FS_SM       = 12          # small labels
FS_LG       = 14          # slightly larger (axis titles etc.)
SW          = 1.5         # main stroke width
SW_THIN     = 1.0         # tick marks and minor lines
SW_HEAVY    = 2.0         # box plot boxes, primary shapes
GRAY        = "#888"      # secondary text / minor elements
GRAY_LT     = "#ccc"      # grid lines
DOT_R       = 4           # default filled dot radius
OPEN_DOT_R  = 5           # open circle radius (inequalities)
LABEL_PAD   = 16          # px gap between shape edge and nearest label

# ═══════════════════════════════════════════════════════════════════════════════
# MATH UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def make_scale(data_min: float, data_max: float,
               px_min: float, px_max: float):
    """
    Build a linear scale function.

    Returns (px_per_unit, to_px) where to_px(value) -> float pixel coordinate.

    Example
    -------
    ppu, to_px = make_scale(-5, 5, 40, 440)
    assert to_px(0) == 240.0
    """
    span = data_max - data_min
    if abs(span) < 1e-12:
        raise ValueError(f"data_min ({data_min}) == data_max ({data_max}): cannot build scale")
    ppu = (px_max - px_min) / span

    def to_px(v: float) -> float:
        return round(px_min + (v - data_min) * ppu, 2)

    return ppu, to_px


def _fmt(v: float) -> str:
    """
    Format a number for SVG display.
    Integers return as plain integers: 3 → "3".
    Other values return as clean decimal: 1.25 → "1.25", 1.333 → "1.333".
    Fraction/mixed-number display is handled by passing pre-formatted label
    strings directly from the spec — see render_rectangle and similar renderers.
    """
    if v == int(v):
        return str(int(v))
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    parts = s.split(".")
    if len(parts) == 2 and len(parts[1]) > 3:
        s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s


def _lbl(v: float) -> str:
    """Axis label: use unicode minus U+2212 for negatives."""
    if v < 0:
        return f"\u2212{_fmt(abs(v))}"
    return _fmt(v)


def _req(spec: dict, *keys: str) -> None:
    """Raise ValueError if any required key is missing from spec."""
    missing = [k for k in keys if k not in spec]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")




def _axis_fs(px_span: float, n_ticks: int, H: int,
             fs_min: float = 10.0, fs_max: float = 22.0) -> float:
    """
    Dynamic font size for axis tick labels.
    Constrained by both canvas height and tick spacing to prevent overlap.
    Same approach as the horizontal number line renderer.
    """
    spacing      = px_span / max(n_ticks, 1)
    fs_by_height  = H * 0.16
    fs_by_spacing = spacing * 0.45
    return round(min(max(fs_min, min(fs_by_height, fs_by_spacing)), fs_max), 1)


def _cell_fs(cell_w: float, cell_h: float,
             fs_min: float = 10.0, fs_max: float = 18.0) -> float:
    """
    Dynamic font size for labels inside bounded cells (area models, tape diagrams,
    fraction strips). Constrained by whichever cell dimension is smaller.
    """
    fs_by_w = cell_w * 0.35
    fs_by_h = cell_h * 0.45
    return round(min(max(fs_min, min(fs_by_w, fs_by_h)), fs_max), 1)


def _stroke_w(H: int) -> float:
    """Stroke width proportional to canvas height."""
    return round(min(max(1.2, H * 0.015), 2.5), 2)


def _unpack(v):
    """
    Unpack a spec value into (float_value, display_label). Handles:
      - (float, str) tuple from notebook cast()  e.g. (1.75, "1¾")
      - Unicode mixed-number string              e.g. "1¾", "2¼", "½"
      - Plain int / float                        e.g. 3, 1.75
    """
    if isinstance(v, tuple) and len(v) == 2:
        return float(v[0]), str(v[1])
    _UF = {
        "\u00bc": 0.25,  # ¼
        "\u00bd": 0.5,   # ½
        "\u00be": 0.75,  # ¾
        "\u2153": 1/3,   # ⅓
        "\u2154": 2/3,   # ⅔
        "\u215b": 0.125, # ⅛
        "\u215c": 0.375, # ⅜
        "\u215d": 0.625, # ⅝
        "\u215e": 0.875, # ⅞
    }
    s = str(v).strip()
    for uf, fval in _UF.items():
        if s.endswith(uf):
            prefix = s[:-len(uf)].strip()
            whole  = int(prefix) if prefix else 0
            return whole + fval, s
    num = float(s)
    return num, _fmt(num)

def _arc(cx: float, cy: float, r: float,
         start_deg: float, end_deg: float) -> str:
    """SVG path string for a pie slice (start/end in degrees, 0 = top)."""
    s_rad = math.radians(start_deg - 90)
    e_rad = math.radians(end_deg - 90)
    x1 = round(cx + r * math.cos(s_rad), 2)
    y1 = round(cy + r * math.sin(s_rad), 2)
    x2 = round(cx + r * math.cos(e_rad), 2)
    y2 = round(cy + r * math.sin(e_rad), 2)
    large = 1 if (end_deg - start_deg) > 180 else 0
    return f"M {cx} {cy} L {x1} {y1} A {r} {r} 0 {large} 1 {x2} {y2} Z"


# ═══════════════════════════════════════════════════════════════════════════════
# SVG ELEMENT BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _a(**kw) -> str:
    """Build an attribute string from keyword args (underscore → hyphen)."""
    return " ".join(f'{k.replace("_","-")}="{v}"' for k, v in kw.items())


def _line(x1, y1, x2, y2, stroke="black", stroke_width=SW, **kw) -> str:
    a = _a(stroke=stroke, stroke_width=stroke_width, **kw)
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {a}/>'


def _rect(x, y, w, h, fill="white", stroke="black",
          stroke_width=SW, **kw) -> str:
    a = _a(fill=fill, stroke=stroke, stroke_width=stroke_width, **kw)
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" {a}/>'


def _txt(x, y, content, anchor="middle", size=FS,
         fill="black", **kw) -> str:
    a = _a(font_family=FONT, font_size=size,
           text_anchor=anchor, fill=fill, **kw)
    return f'<text x="{x}" y="{y}" {a}>{content}</text>'


def _circ(cx, cy, r, fill="black", stroke="black",
          stroke_width=SW, **kw) -> str:
    a = _a(fill=fill, stroke=stroke, stroke_width=stroke_width, **kw)
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" {a}/>'


def _path(d, fill="none", stroke="black", stroke_width=SW, **kw) -> str:
    a = _a(fill=fill, stroke=stroke, stroke_width=stroke_width, **kw)
    return f'<path d="{d}" {a}/>'


def _polygon(points_list, fill="white", stroke="black",
             stroke_width=SW, **kw) -> str:
    pts = " ".join(f"{x},{y}" for x, y in points_list)
    a = _a(fill=fill, stroke=stroke, stroke_width=stroke_width, **kw)
    return f'<polygon points="{pts}" {a}/>'


def _h_arrows(px_left: float, px_right: float, y_axis: float,
              arrow_len: float, arrow_h: float) -> list:
    """
    Build left and right polygon arrowheads for a horizontal axis.
    Uses filled triangles — no SVG markers, no rendering quirks.

    px_left / px_right are the TICK extents.
    Arrowhead tips sit margin pixels beyond those extents.
    Returns list of SVG polygon element strings.
    """
    margin = arrow_len * 0.6   # gap from last tick to arrowhead base

    # Right arrow: tip points right
    tip_r  = round(px_right + margin + arrow_len, 2)
    base_r = round(px_right + margin, 2)
    right_pts = [(tip_r, y_axis),
                 (base_r, round(y_axis - arrow_h, 2)),
                 (base_r, round(y_axis + arrow_h, 2))]

    # Left arrow: tip points left
    tip_l  = round(px_left - margin - arrow_len, 2)
    base_l = round(px_left - margin, 2)
    left_pts = [(tip_l, y_axis),
                (base_l, round(y_axis - arrow_h, 2)),
                (base_l, round(y_axis + arrow_h, 2))]

    return [
        _polygon(right_pts, fill="black", stroke="none"),
        _polygon(left_pts,  fill="black", stroke="none"),
    ]


def _h_axis_elements(axis_min: float, axis_max: float,
                     labeled_interval: float,
                     px_left: float, px_right: float,
                     y_axis: float, to_px,
                     W: int = 480, H: int = 80,
                     unlabeled_interval: float = None,
                     show_arrows: bool = True) -> list:
    """
    Build SVG elements for a horizontal axis.

    All visual dimensions scale proportionally with the canvas size —
    matching the approach from the reference number line script:
      stroke width, tick height, font size, and arrow size all derived
      from H and tick_spacing rather than hardcoded.

    Returns list of SVG element strings.
    """
    # ── Proportional sizing (derived from canvas dimensions)
    # Reference: 700 × 120 canvas at default proportions
    stroke_w     = round(min(max(1.2, H * 0.015), 2.5), 2)
    tick_half    = round(min(max(3.0, H * 0.045), 7.0), 2)
    arrow_len    = round(min(max(10.0, H * 0.14), 20.0), 2)
    arrow_h      = round(min(max(4.0,  H * 0.065), 10.0), 2)

    # Dynamic font size: constrained by both canvas height and tick spacing
    n_ticks      = max(int(round((axis_max - axis_min) / labeled_interval)), 1)
    tick_spacing = (px_right - px_left) / n_ticks
    fs_by_height  = H * 0.16
    fs_by_spacing = tick_spacing * 0.45
    font_size    = round(min(max(8.0, min(fs_by_height, fs_by_spacing)), 22.0), 1)

    # Label offset: geometry-based so labels never clip the canvas bottom.
    # tick_half  = distance from axis line to tick bottom
    # font*0.75  ≈ ascent height (baseline → cap-top in Arial/Lato)
    # +3px gap between tick bottom and character top
    label_offset = round(tick_half + font_size * 0.75 + 3, 2)

    els = []

    # ── Axis line (between the two arrowhead bases, not to the tips)
    margin     = arrow_len * 0.6
    line_left  = round(px_left  - margin, 2) if show_arrows else px_left
    line_right = round(px_right + margin, 2) if show_arrows else px_right
    els.append(_line(line_left, y_axis, line_right, y_axis,
                     stroke_width=stroke_w))

    # ── Polygon arrowheads (replaces SVG marker approach)
    if show_arrows:
        els += _h_arrows(px_left, px_right, y_axis, arrow_len, arrow_h)

    # ── Unlabeled (minor) ticks — skip if None or falsy
    if unlabeled_interval:
        v = axis_min
        while v <= axis_max + 1e-9:
            x = to_px(v)
            els.append(_line(x, y_axis - tick_half * 0.5,
                             x, y_axis + tick_half * 0.5,
                             stroke_width=round(stroke_w * 0.7, 2)))
            v = round(v + unlabeled_interval, 10)

    # ── Labeled (major) ticks
    v = axis_min
    while v <= axis_max + 1e-9:
        x = to_px(v)
        els.append(_line(x, y_axis - tick_half,
                         x, y_axis + tick_half,
                         stroke_width=round(stroke_w * 0.7, 2)))
        els.append(_txt(x, y_axis + label_offset, _lbl(v), size=font_size))
        v = round(v + labeled_interval, 10)

    return els


def _wrap(body: str, w: int, h: int) -> str:
    return (
        f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'xmlns="http://www.w3.org/2000/svg">\n{body}\n</svg>'
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. HORIZONTAL NUMBER LINE — POINTS
# ═══════════════════════════════════════════════════════════════════════════════

def render_number_line_h(spec: dict) -> str:
    """
    Spec keys:
      axis_min          float   left end of axis
      axis_max          float   right end of axis
      labeled_interval  float   e.g. 1 for every integer, 2 for every even
      points            list    [{value, label (optional), open (bool, default False)}]
      axis_label        str     optional label below axis
      width             int     SVG width (default 480)
      height            int     SVG height (default 80)
      show_arrows       bool    default True
      unlabeled_interval float  optional minor tick interval
    """
    _req(spec, "axis_min", "axis_max", "labeled_interval")

    W   = int(spec.get("width", 480))
    H   = int(spec.get("height", 80))
    ML  = 48    # margin left
    MR  = 48    # margin right
    y_ax = H - 28

    ppu, to_px = make_scale(spec["axis_min"], spec["axis_max"],
                             ML, W - MR)

    els = _h_axis_elements(
        spec["axis_min"], spec["axis_max"],
        spec["labeled_interval"],
        ML, W - MR, y_ax, to_px,
        W=W, H=H,
        unlabeled_interval=spec.get("unlabeled_interval"),
        show_arrows=spec.get("show_arrows", True),
    )

    # ── Plot points
    for pt in spec.get("points", []):
        v = pt["value"]
        x = to_px(v)
        open_circle = pt.get("open", False)
        if open_circle:
            els.append(_circ(x, y_ax, OPEN_DOT_R,
                             fill="white", stroke="black", stroke_width=SW))
        else:
            els.append(_circ(x, y_ax, DOT_R, fill="black"))
        if pt.get("label"):
            # Suppress point label if value already shown as a labeled tick mark
            _li   = spec["labeled_interval"]
            _amin = spec["axis_min"]
            _steps = (v - _amin) / _li
            _on_tick = abs(_steps - round(_steps)) < 1e-9
            if not _on_tick:
                els.append(_txt(x, y_ax - 12, pt["label"], size=FS_SM))

    # ── Optional axis label
    if spec.get("axis_label"):
        els.append(_txt(W // 2, H - 4, spec["axis_label"],
                        size=FS_SM, fill=GRAY))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. HORIZONTAL NUMBER LINE — DIRECTIONAL ARROWS (rational number ops)
# ═══════════════════════════════════════════════════════════════════════════════

def render_number_line_h_arrow(spec: dict) -> str:
    """
    Spec keys:
      axis_min, axis_max, labeled_interval
      arrows  list  [{start: float, end: float, label: str (optional),
                      above: bool (default alternating — first True, second False)}]
      points  list  [{value: float}]  — final result dot
      width, height, axis_label
    """
    _req(spec, "axis_min", "axis_max", "labeled_interval", "arrows")

    W      = int(spec.get("width", 480))
    ML     = 48
    MR     = 48
    arrows = spec["arrows"]

    has_below = any(
        not arr.get("above", i % 2 == 0)
        for i, arr in enumerate(arrows)
    )

    # ── Canvas height: use specified value or a default that fits the content.
    # Below-arrows need significantly more vertical room than above-only ones.
    H = int(spec.get("height", 150 if has_below else 110))

    # ── Axis vertical position.
    # When arrows go below: position axis at 38% from top so there is
    # enough room below to arch the arc clearly past the tick labels.
    # When above-only: axis near the bottom as in a standard number line.
    y_ax = round(H * 0.38) if has_below else H - 30

    ppu, to_px = make_scale(spec["axis_min"], spec["axis_max"], ML, W - MR)

    # ── Compute tick label bottom — this is the threshold the below-arc must clear.
    # Use the same formula as _h_axis_elements (with H capped at 80 for font sizing).
    H_font    = min(H, 80)
    n_ticks   = max(int(round((spec["axis_max"] - spec["axis_min"])
                              / spec["labeled_interval"])), 1)
    t_spacing = (W - ML - MR) / n_ticks
    t_font    = round(min(max(8.0, min(H_font * 0.16, t_spacing * 0.45)), 22.0), 1)
    t_half    = round(min(max(3.0, H_font * 0.045), 7.0), 2)
    # Bottom of tick label text (baseline + small descender allowance)
    tick_lbl_bottom = y_ax + t_half + t_font + 4

    # ── Arc offsets.
    # ABOVE: arc peak must clear the top margin (≥ 14px from canvas top)
    space_above  = y_ax - 14
    ABOVE_OFFSET = round(min(space_above * 0.75, 44), 1)

    # BELOW: arc MIDPOINT must be clearly below tick_lbl_bottom.
    # 8px clearance gives visible separation without pushing arc too deep.
    ctrl_y_min   = 2 * (tick_lbl_bottom + 8) - y_ax
    BELOW_OFFSET = round(ctrl_y_min - y_ax, 1)
    # Hard ceiling: leave room for the arc label and bottom padding
    BELOW_OFFSET = min(BELOW_OFFSET, H - y_ax - 26)

    # ── Arrow polygon size
    arrow_len = round(min(max(6.0, H * 0.055), 9.0), 2)
    arrow_h   = round(min(max(2.5, H * 0.030), 4.5), 2)

    els = []
    els += _h_axis_elements(
        spec["axis_min"], spec["axis_max"],
        spec["labeled_interval"],
        ML, W - MR, y_ax, to_px,
        W=W, H=H_font,   # font sized to label area only
        show_arrows=True,
    )

    # ── Draw curved directional arrows — reference style
    # Tangent-based arrowheads follow the arc direction (like the reference image).
    # Result dots are drawn LAST at larger radius to cap any arrowhead overlap cleanly.
    for i, arr in enumerate(arrows):
        x1    = to_px(arr["start"])
        x2    = to_px(arr["end"])
        above = arr.get("above", i % 2 == 0)
        arc_h = -(ABOVE_OFFSET if above else -BELOW_OFFSET)
        mx    = (x1 + x2) / 2
        ctrl_y = y_ax + arc_h

        d = f"M {x1} {y_ax} Q {mx} {ctrl_y} {x2} {y_ax}"
        els.append(f'<path d="{d}" fill="none" stroke="black" '
                   f'stroke-width="{SW}"/>')

        # Polygon arrowhead: tangent direction at t=1 of quadratic bezier
        tx = x2 - mx
        ty = y_ax - ctrl_y
        ln = math.hypot(tx, ty) or 1
        tx, ty = tx / ln, ty / ln
        tip_pts = [
            (round(x2, 2),                                          round(y_ax, 2)),
            (round(x2 - tx * arrow_len + ty * arrow_h, 2),         round(y_ax - ty * arrow_len - tx * arrow_h, 2)),
            (round(x2 - tx * arrow_len - ty * arrow_h, 2),         round(y_ax - ty * arrow_len + tx * arrow_h, 2)),
        ]
        els.append(_polygon(tip_pts, fill="black", stroke="none"))

        # Label at arc peak: above the arc for above-arcs, below for below-arcs
        if arr.get("label"):
            lbl_y = round(ctrl_y - 8, 2) if above else round(ctrl_y + 14, 2)
            lbl_y = max(12.0, min(lbl_y, H - FS_SM - 4))
            els.append(_txt(mx, lbl_y, arr["label"], size=FS_SM))

    if spec.get("axis_label"):
        els.append(_txt(W // 2, H - 4, spec["axis_label"],
                        size=FS_SM, fill=GRAY))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. NUMBER LINE WITH INEQUALITY RAY
# ═══════════════════════════════════════════════════════════════════════════════

def render_number_line_inequality(spec: dict) -> str:
    """
    Spec keys:
      axis_min, axis_max, labeled_interval
      value       float   boundary point
      open        bool    True = open circle (strict), False = closed circle
      direction   str     'left' | 'right'
      width, height
    """
    _req(spec, "axis_min", "axis_max", "labeled_interval", "value", "direction")

    W  = int(spec.get("width", 480))
    H  = int(spec.get("height", 80))
    ML = 48
    MR = 48
    y_ax = H - 28

    ppu, to_px = make_scale(spec["axis_min"], spec["axis_max"], ML, W - MR)

    els = _h_axis_elements(
        spec["axis_min"], spec["axis_max"],
        spec["labeled_interval"],
        ML, W - MR, y_ax, to_px,
        W=W, H=H,
        show_arrows=True,
    )

    bx = to_px(spec["value"])
    is_open = spec.get("open", True)
    go_right = spec["direction"] == "right"

    # ── Ray (heavy line from boundary to edge)
    ray_end = (W - MR + 10) if go_right else (ML - 10)
    els.append(_line(bx, y_ax, ray_end, y_ax,
                     stroke="black", stroke_width=SW_HEAVY))

    # ── Boundary circle
    if is_open:
        els.append(_circ(bx, y_ax, OPEN_DOT_R,
                         fill="white", stroke="black", stroke_width=SW_HEAVY))
    else:
        els.append(_circ(bx, y_ax, OPEN_DOT_R,
                         fill="black", stroke="black", stroke_width=SW_HEAVY))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. VERTICAL NUMBER LINE / THERMOMETER
# ═══════════════════════════════════════════════════════════════════════════════

def render_number_line_v(spec: dict) -> str:
    """
    Spec keys:
      axis_min, axis_max, labeled_interval
      points      list  [{value: float}]
      show_bulb   bool  default False (True = thermometer bulb at bottom)
      axis_label  str   optional label below
      width, height
    """
    _req(spec, "axis_min", "axis_max", "labeled_interval")

    W  = int(spec.get("width", 100))
    H  = int(spec.get("height", 240))
    MT = 20
    MB = 40
    x_ax = W // 2

    ppu, to_py = make_scale(spec["axis_min"], spec["axis_max"],
                             H - MB, MT)   # min maps to bottom

    # ── Dynamic sizing
    interval  = spec["labeled_interval"]
    n_ticks   = max(int(round((spec["axis_max"] - spec["axis_min"]) / interval)), 1)
    px_span   = H - MT - MB
    # For vertical axis: spacing-based constraint uses px_span/n_ticks;
    # canvas-size constraint uses W (width determines how much label space there is)
    fs        = _axis_fs(px_span, n_ticks, W, fs_min=7.0, fs_max=18.0)
    sw        = _stroke_w(H)
    tick_w    = round(min(max(3.0, W * 0.055), 7.0), 2)   # tick half-width
    dot_r     = round(min(max(3.0, min(W, H) * 0.02), 6.0), 1)
    lbl_gap   = tick_w + 6                                  # gap from axis to label

    els = []

    # ── Axis line
    els.append(_line(x_ax, MT, x_ax, H - MB, stroke_width=sw))

    # ── Ticks and labels
    v = spec["axis_min"]
    while v <= spec["axis_max"] + 1e-9:
        y = to_py(v)
        els.append(_line(x_ax - tick_w, y, x_ax + tick_w, y,
                         stroke_width=round(sw * 0.7, 2)))
        els.append(_txt(x_ax + lbl_gap, y + fs * 0.35, _lbl(v),
                        anchor="start", size=fs))
        v = round(v + interval, 10)

    # ── Points
    for pt in spec.get("points", []):
        y = to_py(pt["value"])
        els.append(_circ(x_ax, y, dot_r, fill="black"))

    # ── Optional thermometer bulb (scales with canvas)
    if spec.get("show_bulb", False):
        bulb_r = round(min(max(8.0, W * 0.1), 14.0), 1)
        bulb_y = H - MB + bulb_r + 2
        tube_w = round(bulb_r * 0.45, 1)
        els.append(_circ(x_ax, bulb_y, bulb_r, fill="black"))
        els.append(_rect(x_ax - tube_w, H - MB, tube_w * 2, bulb_r + 4,
                         fill="black", stroke="black"))

    if spec.get("axis_label"):
        els.append(_txt(x_ax, H - 6, spec["axis_label"],
                        size=round(fs * 0.9, 1), fill=GRAY))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DOUBLE NUMBER LINE
# ═══════════════════════════════════════════════════════════════════════════════

def render_double_number_line(spec: dict) -> str:
    """
    Spec keys:
      top_min, top_max, top_interval, top_label
      bottom_min, bottom_max, bottom_interval, bottom_label
      tick_values   list  [{top: float, bottom: float}]  shared tick positions
      width, height
    """
    _req(spec, "top_min", "top_max", "top_interval",
         "bottom_min", "bottom_max", "bottom_interval")

    W   = int(spec.get("width", 480))
    H   = int(spec.get("height", 120))
    ML  = 60
    MR  = 20
    y_top = 40
    y_bot = 80

    ppu_t, to_top = make_scale(spec["top_min"], spec["top_max"], ML, W - MR)
    ppu_b, to_bot = make_scale(spec["bottom_min"], spec["bottom_max"], ML, W - MR)

    # Pre-populate axis line slots so dynamic section can overwrite them by index
    els = [None, None]

    # ── Dynamic font sizes — each axis independent
    # Cap at H=80 so the gap between axes doesn't inflate font size
    H_font    = min(H, 80)
    px_span   = W - ML - MR
    n_top     = max(int(round((spec["top_max"] - spec["top_min"]) / spec["top_interval"])), 1)
    n_bot     = max(int(round((spec["bottom_max"] - spec["bottom_min"]) / spec["bottom_interval"])), 1)
    fs_top    = _axis_fs(px_span, n_top, H_font)
    fs_bot    = _axis_fs(px_span, n_bot, H_font)
    sw        = _stroke_w(H_font)
    tick_h    = round(min(max(3.0, H_font * 0.04), 6.0), 2)

    # ── Two axis lines
    els[0] = _line(ML, y_top, W - MR, y_top, stroke_width=sw)
    els[1] = _line(ML, y_bot, W - MR, y_bot, stroke_width=sw)

    # ── Top ticks and labels
    v = spec["top_min"]
    while v <= spec["top_max"] + 1e-9:
        x = to_top(v)
        els.append(_line(x, y_top - tick_h, x, y_top + tick_h, stroke_width=round(sw * 0.7, 2)))
        els.append(_txt(x, y_top - tick_h - 4, _lbl(v), size=fs_top))
        v = round(v + spec["top_interval"], 10)

    # ── Bottom ticks and labels
    v = spec["bottom_min"]
    while v <= spec["bottom_max"] + 1e-9:
        x = to_bot(v)
        els.append(_line(x, y_bot - tick_h, x, y_bot + tick_h, stroke_width=round(sw * 0.7, 2)))
        els.append(_txt(x, y_bot + tick_h + 10, _lbl(v), size=fs_bot))
        v = round(v + spec["bottom_interval"], 10)

    # ── Vertical connectors at shared tick values
    for pair in spec.get("tick_values", []):
        x_t = to_top(pair["top"])
        x_b = to_bot(pair["bottom"])
        # Draw connector between the two lines at corresponding positions
        els.append(_line(x_t, y_top, x_b, y_bot,
                         stroke=GRAY_LT, stroke_width=SW_THIN))

    # ── Labels
    if spec.get("top_label"):
        els.append(_txt(ML - 8, y_top + 4, spec["top_label"],
                        anchor="end", size=FS_SM))
    if spec.get("bottom_label"):
        els.append(_txt(ML - 8, y_bot + 4, spec["bottom_label"],
                        anchor="end", size=FS_SM))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. FRACTION STRIP
# ═══════════════════════════════════════════════════════════════════════════════

def render_fraction_strip(spec: dict) -> str:
    """
    Spec keys:
      strips  list  [{numerator, denominator, label (optional), shaded_parts (list of 0-based indices)}]
      width, height (height per strip, default 32)
    """
    _req(spec, "strips")

    W        = int(spec.get("width", 400))
    ROW_H    = int(spec.get("strip_height", 32))
    ML       = 60    # space for label on left
    MR       = 12
    strip_w  = W - ML - MR
    n_strips = len(spec["strips"])
    H        = n_strips * (ROW_H + 8) + 20

    els = []

    for i, strip in enumerate(spec["strips"]):
        d    = int(strip["denominator"])
        n    = int(strip["numerator"])
        y    = 12 + i * (ROW_H + 8)
        unit = strip_w / d
        shaded = set(strip.get("shaded_parts", list(range(n))))

        # ── Dynamic font: constrained by unit cell width and strip height
        fs_lbl  = _cell_fs(strip_w * 0.35, ROW_H)   # row label on left
        fs_part = _cell_fs(unit * 0.8, ROW_H * 0.6) # optional per-part label

        # ── Label on left
        if strip.get("label"):
            els.append(_txt(ML - 8, y + ROW_H // 2 + 4,
                            strip["label"], anchor="end", size=fs_lbl))

        # ── Draw each part
        for j in range(d):
            x   = ML + j * unit
            fll = GRAY_LT if j in shaded else "white"
            els.append(_rect(round(x, 2), y, round(unit, 2), ROW_H,
                             fill=fll, stroke_width=SW_THIN))
            # Optional per-cell label (e.g. fraction value)
            if strip.get("show_values"):
                els.append(_txt(round(x + unit / 2, 2), y + ROW_H // 2 + 4,
                                f"1/{d}", size=fs_part))

        # ── Outer border (heavier)
        sw = _stroke_w(ROW_H * n_strips)
        els.append(_rect(ML, y, strip_w, ROW_H, fill="none", stroke_width=sw))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. TAPE DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════

def render_tape_diagram(spec: dict) -> str:
    """
    Spec keys:
      parts       list  [{label, value (float|None), shaded (bool, default False)}]
      total_label str   optional — shown above bracket
      unit_width  float optional — fixed px width per value unit
      width, height
    """
    _req(spec, "parts")

    W        = int(spec.get("width", 400))
    has_lbl  = bool(spec.get("total_label"))
    # Reserve 32px at the top for the bracket + label when present
    TOP_PAD  = 32 if has_lbl else 8
    H        = int(spec.get("height", TOP_PAD + 36 + 8))
    ML       = 20
    MR       = 20
    bar_h    = 36
    bar_y    = TOP_PAD  # bar starts after top padding

    parts  = spec["parts"]
    total  = sum(p.get("value", 1) for p in parts)
    if total == 0:
        total = len(parts)

    avail  = W - ML - MR
    els    = []

    # ── Dynamic font: constrained by narrowest segment
    vals_list = [p.get("value", 1) or 1 for p in parts]
    min_v     = min(vals_list)
    min_pw    = avail * (min_v / total)
    fs_seg    = _cell_fs(min_pw * 0.85, bar_h * 0.6)
    sw        = _stroke_w(bar_h * len(parts))

    x = ML
    for p in parts:
        v   = p.get("value", 1) or 1
        pw  = avail * (v / total)
        fll = GRAY_LT if p.get("shaded", False) else "white"
        els.append(_rect(round(x, 2), bar_y, round(pw, 2), bar_h,
                         fill=fll, stroke_width=sw))
        if p.get("label"):
            els.append(_txt(round(x + pw / 2, 2),
                            bar_y + bar_h // 2 + fs_seg * 0.35,
                            p["label"], size=fs_seg))
        x = round(x + pw, 2)

    # ── Total label above with bracket
    if spec.get("total_label"):
        bry = bar_y - 14
        els.append(_line(ML, bry, W - MR, bry, stroke_width=SW_THIN))
        els.append(_line(ML, bry, ML, bry + 6, stroke_width=SW_THIN))
        els.append(_line(W - MR, bry, W - MR, bry + 6, stroke_width=SW_THIN))
        els.append(_txt((ML + W - MR) / 2, bry - 4,
                        spec["total_label"], size=FS))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. AREA MODEL — FRACTION × FRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def render_area_model_fraction(spec: dict) -> str:
    """
    Spec keys:
      total_rows      int   denominator of first fraction (vertical)
      total_cols      int   denominator of second fraction (horizontal)
      shaded_rows     int   numerator of first fraction
      shaded_cols     int   numerator of second fraction
      row_label       str   label for left side (e.g. "3/4")
      col_label       str   label for top (e.g. "2/3")
      width, height
    """
    _req(spec, "total_rows", "total_cols", "shaded_rows", "shaded_cols")

    W  = int(spec.get("width", 280))
    H  = int(spec.get("height", 280))
    ML = 48
    MT = 48
    MR = 16
    MB = 16

    grid_w  = W - ML - MR
    grid_h  = H - MT - MB
    rows    = int(spec["total_rows"])
    cols    = int(spec["total_cols"])
    s_rows  = int(spec["shaded_rows"])
    s_cols  = int(spec["shaded_cols"])
    cw      = grid_w / cols
    rh      = grid_h / rows

    els = []

    fs_cell = _cell_fs(cw, rh)   # font for any per-cell label

    for r in range(rows):
        for c in range(cols):
            x   = ML + c * cw
            y   = MT + r * rh
            if r < s_rows and c < s_cols:
                fll = GRAY
            elif r < s_rows or c < s_cols:
                fll = GRAY_LT
            else:
                fll = "white"
            els.append(_rect(round(x, 2), round(y, 2),
                             round(cw, 2), round(rh, 2),
                             fill=fll, stroke_width=SW_THIN))

    sw = _stroke_w(min(grid_w, grid_h))
    els.append(_rect(ML, MT, grid_w, grid_h, fill="none", stroke_width=sw))

    # ── Column label (top) and row label (left)
    if spec.get("col_label"):
        # Bracket over shaded columns
        bx = ML + s_cols * cw
        els.append(_line(ML, MT - 12, bx, MT - 12, stroke_width=SW_THIN))
        els.append(_line(ML, MT - 12, ML, MT - 6, stroke_width=SW_THIN))
        els.append(_line(bx, MT - 12, bx, MT - 6, stroke_width=SW_THIN))
        els.append(_txt((ML + bx) / 2, MT - 18,
                        spec["col_label"], size=FS))
    if spec.get("row_label"):
        by = MT + s_rows * rh
        # Bracket to the left
        els.append(_line(ML - 12, MT, ML - 12, by, stroke_width=SW_THIN))
        els.append(_line(ML - 12, MT, ML - 6, MT, stroke_width=SW_THIN))
        els.append(_line(ML - 12, by, ML - 6, by, stroke_width=SW_THIN))
        mid_y = (MT + by) / 2
        els.append(_txt(ML - 20, mid_y + 4, spec["row_label"],
                        anchor="end", size=FS))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. AREA MODEL — PARTIAL PRODUCTS (whole number multiplication)
# ═══════════════════════════════════════════════════════════════════════════════

def render_area_model_multiplication(spec: dict) -> str:
    """
    Spec keys:
      row_parts   list of float   e.g. [20, 3] for 23
      col_parts   list of float   e.g. [10, 5] for 15
      show_products bool          show product in each cell (default True)
      width, height
    """
    _req(spec, "row_parts", "col_parts")

    W  = int(spec.get("width", 320))
    H  = int(spec.get("height", 240))
    ML = 52
    MT = 52
    MR = 16
    MB = 16

    row_parts = spec["row_parts"]   # vertical split
    col_parts = spec["col_parts"]   # horizontal split

    row_total = sum(row_parts)
    col_total = sum(col_parts)
    grid_w    = W - ML - MR
    grid_h    = H - MT - MB

    show_p = spec.get("show_products", True)
    els    = []

    col_ws = [grid_w * c / col_total for c in col_parts]
    row_hs = [grid_h * r / row_total for r in row_parts]

    # ── Dynamic font: smallest cell determines the ceiling
    min_cw  = min(col_ws)
    min_rh  = min(row_hs)
    fs_cell = _cell_fs(min_cw, min_rh)
    fs_hdr  = _cell_fs(min_cw, MT * 0.6)    # header labels above/left of grid
    sw      = _stroke_w(min(grid_w, grid_h))

    y = MT
    for ri, rh in enumerate(row_hs):
        x = ML
        for ci, cw in enumerate(col_ws):
            els.append(_rect(round(x, 2), round(y, 2),
                             round(cw, 2), round(rh, 2),
                             fill="white", stroke_width=round(sw * 0.7, 2)))
            if show_p:
                product = row_parts[ri] * col_parts[ci]
                els.append(_txt(round(x + cw / 2, 2),
                                round(y + rh / 2 + fs_cell * 0.35, 2),
                                _fmt(product), size=fs_cell))
            x = round(x + cw, 2)
        y = round(y + rh, 2)

    els.append(_rect(ML, MT, grid_w, grid_h, fill="none", stroke_width=sw))

    x = ML
    for ci, cw in enumerate(col_ws):
        els.append(_txt(round(x + cw / 2, 2), MT - 6,
                        _fmt(col_parts[ci]), size=fs_hdr))
        x = round(x + cw, 2)

    y = MT
    for ri, rh in enumerate(row_hs):
        els.append(_txt(ML - 6, round(y + rh / 2 + fs_hdr * 0.35, 2),
                        _fmt(row_parts[ri]),
                        anchor="end", size=fs_hdr))
        y = round(y + rh, 2)

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. ARRAY (ROWS × COLUMNS)
# ═══════════════════════════════════════════════════════════════════════════════

def render_array(spec: dict) -> str:
    """
    Spec keys:
      rows      int
      cols      int
      dot_radius  int  default 5
      gap         int  default 22  (px between dot centers)
      width, height (computed from rows/cols if not provided)
    """
    _req(spec, "rows", "cols")

    rows = int(spec["rows"])
    cols = int(spec["cols"])
    r    = int(spec.get("dot_radius", 5))
    gap  = int(spec.get("gap", 22))
    pad  = 20

    W = cols * gap + 2 * pad
    H = rows * gap + 2 * pad
    W = int(spec.get("width", W))
    H = int(spec.get("height", H))

    # Recompute gap to fit within W/H if overridden
    g_x = (W - 2 * pad) / max(cols - 1, 1) if cols > 1 else 0
    g_y = (H - 2 * pad) / max(rows - 1, 1) if rows > 1 else 0

    els = []
    for row in range(rows):
        for col in range(cols):
            cx = pad + col * g_x if cols > 1 else W // 2
            cy = pad + row * g_y if rows > 1 else H // 2
            els.append(_circ(round(cx, 2), round(cy, 2), r, fill="black"))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. LABELED RECTANGLE
# ═══════════════════════════════════════════════════════════════════════════════

def render_rectangle(spec: dict) -> str:
    """
    Spec keys:
      width_value   float
      height_value  float
      unit          str    e.g. "inches" or "cm"
      show_right_angle  bool  default False
      width, height (SVG canvas)
    """
    _req(spec, "width_value", "height_value")

    wv,  w_lbl_val = _unpack(spec["width_value"])
    hv,  h_lbl_val = _unpack(spec["height_value"])
    unit = spec.get("unit", "")
    W   = int(spec.get("width", 320))
    H   = int(spec.get("height", 240))

    # Proportional sizing with padding for labels
    pad    = 52   # space for labels on all sides
    avail_w = W - 2 * pad
    avail_h = H - 2 * pad
    ratio  = wv / hv

    if ratio > avail_w / avail_h:
        rw = avail_w
        rh = avail_w / ratio
    else:
        rh = avail_h
        rw = avail_h * ratio

    rx = (W - rw) / 2
    ry = (H - rh) / 2

    els = []
    els.append(_rect(round(rx, 2), round(ry, 2),
                     round(rw, 2), round(rh, 2),
                     fill="white", stroke_width=SW))

    # ── Width label (top, outside shape, with 15px clearance)
    w_lbl = spec.get("width_label",  f"{w_lbl_val} {unit}").strip()
    els.append(_txt(round(rx + rw / 2, 2), round(ry - LABEL_PAD, 2),
                    w_lbl, size=FS))

    # ── Height label (left side, horizontal)
    h_lbl = spec.get("height_label", f"{h_lbl_val} {unit}").strip()
    mid_y  = round(ry + rh / 2 + FS / 3, 2)   # vertically centred
    mid_x  = round(rx - LABEL_PAD - 2, 2)       # just left of rectangle
    els.append(
        f'<text x="{mid_x}" y="{mid_y}" '
        f'font-family="{FONT}" font-size="{FS}" text-anchor="end" fill="black">'
        f'{h_lbl}</text>'
    )

    # ── Right angle symbol
    if spec.get("show_right_angle", False):
        sq = 8
        els.append(_line(rx + sq, ry, rx + sq, ry + sq, stroke_width=SW_THIN))
        els.append(_line(rx, ry + sq, rx + sq, ry + sq, stroke_width=SW_THIN))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. PARALLELOGRAM
# ═══════════════════════════════════════════════════════════════════════════════

def render_parallelogram(spec: dict) -> str:
    """
    Spec keys:
      base_value, height_value, unit
      slant_offset_fraction  float  how far the top is offset as fraction of base (default 0.25)
      width, height (SVG)
    """
    _req(spec, "base_value", "height_value")

    bv,  b_lbl_val = _unpack(spec["base_value"])
    hv,  h_lbl_val = _unpack(spec["height_value"])
    unit = spec.get("unit", "")
    W    = int(spec.get("width", 340))
    H    = int(spec.get("height", 200))
    slant_frac = float(spec.get("slant_offset_fraction", 0.25))

    pad  = 52
    avail_w = W - 2 * pad
    avail_h = H - 2 * pad

    # Scale base and height proportionally
    ratio = bv / hv
    if ratio > avail_w / avail_h:
        bw = avail_w * 0.8     # leave room for slant
        bh = bw / ratio
    else:
        bh = avail_h
        bw = bh * ratio

    slant = bw * slant_frac
    bx = (W - bw - slant) / 2 + slant
    by = (H - bh) / 2

    # Four corners: bottom-left, bottom-right, top-right, top-left
    pts = [
        (round(bx - slant, 2),       round(by + bh, 2)),
        (round(bx - slant + bw, 2),  round(by + bh, 2)),
        (round(bx + bw, 2),          round(by, 2)),
        (round(bx, 2),               round(by, 2)),
    ]

    els = []
    els.append(_polygon(pts, fill="white", stroke_width=SW))

    # ── Base label (bottom center)
    b_lbl = f"{b_lbl_val} {unit}".strip()
    els.append(_txt(round(pts[0][0] + bw / 2, 2),
                    round(pts[0][1] + LABEL_PAD, 2),
                    b_lbl, size=FS))

    # ── Height label — dashed vertical line + label
    hx = bx + bw * 0.6
    els.append(_line(hx, by, hx, by + bh,
                     stroke=GRAY, stroke_width=SW_THIN,
                     stroke_dasharray="4,3"))
    els.append(_line(hx - 4, by, hx + 4, by, stroke_width=SW_THIN))
    els.append(_line(hx - 4, by + bh, hx + 4, by + bh, stroke_width=SW_THIN))
    h_lbl = f"{_fmt(hv)} {unit}".strip()
    els.append(_txt(hx + 10, round(by + bh / 2 + 4, 2),
                    h_lbl, anchor="start", size=FS))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. TRIANGLE
# ═══════════════════════════════════════════════════════════════════════════════

def render_triangle(spec: dict) -> str:
    """
    Spec keys:
      base_value, height_value, unit
      triangle_type  str  'right' | 'isosceles' | 'scalene' (default 'scalene')
      width, height (SVG)
    """
    _req(spec, "base_value", "height_value")

    bv,  b_lbl_val = _unpack(spec["base_value"])
    hv,  h_lbl_val = _unpack(spec["height_value"])
    unit = spec.get("unit", "")
    tri  = spec.get("triangle_type", "scalene")
    W    = int(spec.get("width", 320))
    H    = int(spec.get("height", 220))

    pad     = 52
    avail_w = W - 2 * pad
    avail_h = H - 2 * pad
    ratio   = bv / hv

    if ratio > avail_w / avail_h:
        bw = avail_w
        bh = bw / ratio
    else:
        bh = avail_h
        bw = bh * ratio

    bx = (W - bw) / 2
    by = (H - bh) / 2

    # Apex x depends on type
    if tri == "right":
        apex_x = bx          # right angle at bottom-left
    elif tri == "isosceles":
        apex_x = bx + bw / 2
    else:
        apex_x = bx + bw * 0.35

    pts = [
        (round(bx, 2),        round(by + bh, 2)),   # bottom-left
        (round(bx + bw, 2),   round(by + bh, 2)),   # bottom-right
        (round(apex_x, 2),    round(by, 2)),          # apex
    ]

    els = []
    els.append(_polygon(pts, fill="white", stroke_width=SW))

    # ── Right angle symbol if right triangle
    if tri == "right":
        sq = 8
        els.append(_line(bx + sq, by + bh, bx + sq, by + bh - sq,
                         stroke_width=SW_THIN))
        els.append(_line(bx, by + bh - sq, bx + sq, by + bh - sq,
                         stroke_width=SW_THIN))

    # ── Base label (bottom)
    b_lbl = f"{b_lbl_val} {unit}".strip()
    els.append(_txt(round(bx + bw / 2, 2),
                    round(by + bh + LABEL_PAD, 2),
                    b_lbl, size=FS))

    # ── Height — dashed vertical line from apex to base
    els.append(_line(apex_x, by, apex_x, by + bh,
                     stroke=GRAY, stroke_width=SW_THIN,
                     stroke_dasharray="4,3"))
    h_lbl = f"{h_lbl_val} {unit}".strip()
    els.append(_txt(round(apex_x + 12, 2),
                    round(by + bh / 2 + 4, 2),
                    h_lbl, anchor="start", size=FS))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. CIRCLE
# ═══════════════════════════════════════════════════════════════════════════════

def render_circle(spec: dict) -> str:
    """
    Spec keys:
      radius_value   float  (provide this OR diameter_value)
      diameter_value float
      unit           str
      show_radius    bool  default True
      show_diameter  bool  default False
      width, height
    """
    _rv_raw = spec.get("radius_value")
    _dv_raw = spec.get("diameter_value")
    if _rv_raw is None and _dv_raw is None:
        raise ValueError("circle spec needs radius_value or diameter_value")
    if _rv_raw is None:
        dv, d_lbl_val = _unpack(_dv_raw)
        rv = dv / 2; r_lbl_val = _fmt(rv)
    else:
        rv, r_lbl_val = _unpack(_rv_raw)
        if _dv_raw is None:
            dv = rv * 2; d_lbl_val = _fmt(dv)
        else:
            dv, d_lbl_val = _unpack(_dv_raw)

    unit = spec.get("unit", "")
    W    = int(spec.get("width", 220))
    H    = int(spec.get("height", 220))
    pad  = 48

    r_px = min(W, H) / 2 - pad
    cx   = W / 2
    cy   = H / 2

    els = []
    els.append(_circ(round(cx, 2), round(cy, 2), round(r_px, 2),
                     fill="white", stroke_width=SW))

    if spec.get("show_radius", True):
        # Radius line to right
        els.append(_line(cx, cy, cx + r_px, cy, stroke_width=SW_THIN))
        r_lbl = f"r = {r_lbl_val} {unit}".strip()
        els.append(_txt(round(cx + r_px / 2, 2), cy - 8,
                        r_lbl, size=FS))

    if spec.get("show_diameter", False):
        # Full diameter line
        els.append(_line(cx - r_px, cy, cx + r_px, cy,
                         stroke_width=SW_THIN))
        d_lbl = f"d = {d_lbl_val} {unit}".strip()
        els.append(_txt(round(cx, 2), cy + 16, d_lbl, size=FS))

    # ── Center dot
    els.append(_circ(round(cx, 2), round(cy, 2), 3, fill="black"))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. RIGHT TRIANGLE (Pythagorean theorem)
# ═══════════════════════════════════════════════════════════════════════════════

def render_right_triangle(spec: dict) -> str:
    """
    Spec keys:
      leg_a_value     float  horizontal leg
      leg_b_value     float  vertical leg
      hypotenuse_value float  optional — shown as label if provided
      unit            str
      width, height
    """
    _req(spec, "leg_a_value", "leg_b_value")

    av,  a_lbl_val = _unpack(spec["leg_a_value"])
    bv,  b_lbl_val = _unpack(spec["leg_b_value"])
    _hv_raw = spec.get("hypotenuse_value")
    hv, h_lbl_val  = (_unpack(_hv_raw) if _hv_raw is not None else (None, None))
    unit = spec.get("unit", "")
    W    = int(spec.get("width", 280))
    H    = int(spec.get("height", 240))

    pad     = 56
    avail_w = W - 2 * pad
    avail_h = H - 2 * pad
    ratio   = av / bv

    if ratio > avail_w / avail_h:
        tw = avail_w
        th = tw / ratio
    else:
        th = avail_h
        tw = th * ratio

    # Right angle at bottom-left
    ox  = (W - tw) / 2
    oy  = (H - th) / 2 + th   # bottom-left corner

    pts = [
        (round(ox, 2),       round(oy, 2)),            # bottom-left (right angle)
        (round(ox + tw, 2),  round(oy, 2)),            # bottom-right
        (round(ox, 2),       round(oy - th, 2)),       # top-left
    ]

    els = []
    els.append(_polygon(pts, fill="white", stroke_width=SW))

    # ── Right angle marker
    sq = 8
    els.append(_line(ox + sq, oy, ox + sq, oy - sq, stroke_width=SW_THIN))
    els.append(_line(ox, oy - sq, ox + sq, oy - sq, stroke_width=SW_THIN))

    # ── Leg a label (bottom)
    a_lbl = f"{a_lbl_val} {unit}".strip()
    els.append(_txt(round(ox + tw / 2, 2), round(oy + LABEL_PAD, 2),
                    a_lbl, size=FS))

    # ── Leg b label (left, rotated)
    b_lbl = f"{b_lbl_val} {unit}".strip()
    mid_x = ox - LABEL_PAD
    mid_y = oy - th / 2
    els.append(
        f'<text x="{round(mid_x,2)}" y="{round(mid_y,2)}" '
        f'font-family="{FONT}" font-size="{FS}" text-anchor="middle" fill="black" '
        f'transform="rotate(-90 {round(mid_x,2)} {round(mid_y,2)})">'
        f'{b_lbl}</text>'
    )

    # ── Hypotenuse label: parallel to hypotenuse, offset outward, always readable
    if hv is not None:
        # The hypotenuse runs from top-left (ox, oy-th) to bottom-right (ox+tw, oy).
        # We use this LEFT→RIGHT direction so the rotation angle is in [0°, 90°]
        # and text is never upside-down.
        dx_h   = tw
        dy_h   = th          # in SVG: going right and DOWN = bottom-right direction
        hyp_len = math.hypot(dx_h, dy_h)

        # Rotation to match the text to the hypotenuse (going upper-left → lower-right)
        rot_angle = round(math.degrees(math.atan2(dy_h, dx_h)), 1)  # ≈ +53° for 3-4-5

        # Midpoint of hypotenuse
        hx_mid = ox + tw / 2
        hy_mid = oy - th / 2

        # Outward normal: rotate edge direction (dx_h, dy_h) 90° CLOCKWISE → (dy_h, -dx_h).
        # The right-angle is at bottom-left; the outward direction from the hypotenuse
        # is upper-right (positive x, negative y in SVG), which is (th/hyp, -tw/hyp).
        nx =  dy_h / hyp_len   # = th/hyp  → rightward
        ny = -dx_h / hyp_len   # = -tw/hyp → upward in SVG
        OFFSET = LABEL_PAD * 1.4   # enough clearance that text never touches the line
        lx = round(hx_mid + nx * OFFSET, 2)
        ly = round(hy_mid + ny * OFFSET, 2)

        h_lbl = f"{h_lbl_val} {unit}".strip()
        els.append(
            f'<text x="{lx}" y="{ly}" '
            f'font-family="{FONT}" font-size="{FS}" text-anchor="middle" fill="black" '
            f'transform="rotate({rot_angle} {lx} {ly})">'
            f'{h_lbl}</text>'
        )

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 16 & 17. COORDINATE PLANE (Q1 and all four quadrants)
# ═══════════════════════════════════════════════════════════════════════════════

def _coord_plane_base(x_min, x_max, x_int,
                      y_min, y_max, y_int,
                      x_label, y_label,
                      W, H, ML, MR, MT, MB,
                      grid=False):
    """
    Build base coordinate plane SVG elements.
    Returns (els, to_x, to_y).
    """
    # ── Dynamic sizing (cap at 80 to prevent oversized labels on large canvases)
    n_x     = max(int(round((x_max - x_min) / x_int)), 1)
    n_y     = max(int(round((y_max - y_min) / y_int)), 1)
    fs_x    = _axis_fs(W - ML - MR, n_x, min(H, 80))
    fs_y    = _axis_fs(H - MT - MB, n_y, min(W, 80))
    sw      = _stroke_w(min(W, H))
    tick_h  = round(min(max(3.0, min(W, H) * 0.012), 6.0), 2)
    arr_len = round(min(max(8.0, min(W, H) * 0.025), 14.0), 2)
    arr_h   = round(min(max(4.0, min(W, H) * 0.016), 8.0), 2)

    # Gap between last tick and arrowhead base — prevents tick/arrow overlap
    ARROW_GAP = round(arr_len * 1.2, 1)

    # ── Arrowhead tip/base positions (tips clamped inside canvas)
    x_tip   = min(W - MR + arr_len, W - MR)       # positive x tip (right)
    x_base  = x_tip - arr_len
    y_tip   = max(MT - arr_len, int(fs_y) + 4)    # positive y tip (top)
    y_base  = y_tip + arr_len
    xl_tip  = max(ML - arr_len, 4)                # negative x tip (left)
    xl_base = xl_tip + arr_len
    yb_tip  = min(H - MB + arr_len, H - 4)        # negative y tip (bottom)
    yb_base = yb_tip - arr_len

    # ── Scale ranges: ticks stop ARROW_GAP before each arrowhead base
    px_right  = x_base  - ARROW_GAP               # rightmost x tick pixel
    px_top    = y_base  + ARROW_GAP               # topmost y tick (SVG y-down)
    px_left   = (xl_base + ARROW_GAP) if x_min < -1e-9 else ML
    px_bottom = (yb_base - ARROW_GAP) if y_min < -1e-9 else H - MB

    _, to_x = make_scale(x_min, x_max, px_left,  px_right)
    _, to_y = make_scale(y_min, y_max, px_bottom, px_top)   # y flipped

    x0 = to_x(0)
    y0 = to_y(0)

    els = []

    # ── Grid lines
    if grid:
        v = x_min
        while v <= x_max + 1e-9:
            els.append(_line(to_x(v), MT, to_x(v), H - MB,
                             stroke=GRAY_LT, stroke_width=0.5))
            v = round(v + x_int, 10)
        v = y_min
        while v <= y_max + 1e-9:
            els.append(_line(ML, to_y(v), W - MR, to_y(v),
                             stroke=GRAY_LT, stroke_width=0.5))
            v = round(v + y_int, 10)

    # ── Positive x-axis: full line then arrowhead
    els.append(_line(px_left, y0, x_base, y0, stroke_width=sw))
    els.append(_polygon([(x_tip,  y0),
                          (x_base, y0 - arr_h),
                          (x_base, y0 + arr_h)],
                         fill="black", stroke="none"))

    # ── Positive y-axis: full line then arrowhead
    els.append(_line(x0, px_bottom, x0, y_base, stroke_width=sw))
    els.append(_polygon([(x0,         y_tip),
                          (x0 - arr_h, y_base),
                          (x0 + arr_h, y_base)],
                         fill="black", stroke="none"))

    # ── Negative arrowheads (4Q only)
    if x_min < -1e-9:
        els.append(_polygon([(xl_tip,  y0),
                              (xl_base, y0 - arr_h),
                              (xl_base, y0 + arr_h)],
                             fill="black", stroke="none"))
    if y_min < -1e-9:
        els.append(_polygon([(x0,         yb_tip),
                              (x0 - arr_h, yb_base),
                              (x0 + arr_h, yb_base)],
                             fill="black", stroke="none"))

    # ── X ticks and labels
    v = x_min
    while v <= x_max + 1e-9:
        if abs(v) < 1e-9:
            v = round(v + x_int, 10)
            continue
        x = to_x(v)
        els.append(_line(x, y0 - tick_h, x, y0 + tick_h,
                         stroke_width=round(sw * 0.7, 2)))
        els.append(_txt(x, y0 + tick_h + fs_x + 2, _lbl(v), size=fs_x))
        v = round(v + x_int, 10)

    # ── Y ticks and labels
    v = y_min
    while v <= y_max + 1e-9:
        if abs(v) < 1e-9:
            v = round(v + y_int, 10)
            continue
        y = to_y(v)
        els.append(_line(x0 - tick_h, y, x0 + tick_h, y,
                         stroke_width=round(sw * 0.7, 2)))
        els.append(_txt(x0 - tick_h - 4, y + fs_y * 0.35, _lbl(v),
                        anchor="end", size=fs_y))
        v = round(v + y_int, 10)

    # ── Axis labels at arrowhead tips
    if x_label:
        els.append(_txt(round(x_tip + 4, 2), round(y0 + fs_x * 0.35, 2),
                        x_label, anchor="start", size=fs_x, fill="black"))
    if y_label:
        els.append(_txt(round(x0, 2), max(y_tip - 4, int(fs_y) + 2),
                        y_label, anchor="middle", size=fs_y, fill="black"))

    return els, to_x, to_y


def render_coordinate_q1(spec: dict) -> str:
    """
    Spec keys:
      x_max, y_max, x_interval, y_interval
      x_label, y_label
      points  list  [{x, y, label (optional)}]
      grid    bool  default True
      width, height
    """
    _req(spec, "x_max", "y_max")

    W  = int(spec.get("width", 320))
    H  = int(spec.get("height", 320))
    ML = 44
    MR = 24
    MT = 40
    MB = 44

    x_int = float(spec.get("x_interval", 1))
    y_int = float(spec.get("y_interval", 1))

    els, to_x, to_y = _coord_plane_base(
        0, float(spec["x_max"]), x_int,
        0, float(spec["y_max"]), y_int,
        spec.get("x_label", ""), spec.get("y_label", ""),
        W, H, ML, MR, MT, MB,
        grid=spec.get("grid", True)
    )

    for pt in spec.get("points", []):
        x = to_x(pt["x"])
        y = to_y(pt["y"])
        els.append(_circ(x, y, DOT_R, fill="black"))
        if pt.get("label"):
            els.append(_txt(x + 8, y - 6, pt["label"],
                            anchor="start", size=FS_SM))

    return _wrap("\n".join(els), W, H)


def render_coordinate_4q(spec: dict) -> str:
    """
    Spec keys:
      x_min, x_max, y_min, y_max, x_interval, y_interval
      x_label, y_label
      points  list  [{x, y, label (optional)}]
      grid    bool  default True
      width, height
    """
    _req(spec, "x_min", "x_max", "y_min", "y_max")

    W  = int(spec.get("width", 360))
    H  = int(spec.get("height", 360))
    ML = 50
    MR = 24
    MT = 40
    MB = 44

    x_int = float(spec.get("x_interval", 1))
    y_int = float(spec.get("y_interval", 1))

    els, to_x, to_y = _coord_plane_base(
        float(spec["x_min"]), float(spec["x_max"]), x_int,
        float(spec["y_min"]), float(spec["y_max"]), y_int,
        spec.get("x_label", ""), spec.get("y_label", ""),
        W, H, ML, MR, MT, MB,
        grid=spec.get("grid", True)
    )

    for pt in spec.get("points", []):
        x = to_x(pt["x"])
        y = to_y(pt["y"])
        els.append(_circ(x, y, DOT_R, fill="black"))
        if pt.get("label"):
            els.append(_txt(x + 8, y - 6, pt["label"],
                            anchor="start", size=FS_SM))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. COORDINATE PLANE WITH LINEAR GRAPH(S)
# ═══════════════════════════════════════════════════════════════════════════════

def render_linear_graph(spec: dict) -> str:
    """
    Spec keys:
      x_min, x_max, y_min, y_max, x_interval, y_interval
      x_label, y_label
      lines  list  [{x1, y1, x2, y2, label (optional), dashed (bool)}]
      points list  [{x, y, label}]
      grid   bool  default True
      width, height
    """
    _req(spec, "x_min", "x_max", "y_min", "y_max", "lines")

    W  = int(spec.get("width", 360))
    H  = int(spec.get("height", 360))
    ML = 50
    MR = 24
    MT = 40
    MB = 44

    x_int = float(spec.get("x_interval", 1))
    y_int = float(spec.get("y_interval", 1))

    els, to_x, to_y = _coord_plane_base(
        float(spec["x_min"]), float(spec["x_max"]), x_int,
        float(spec["y_min"]), float(spec["y_max"]), y_int,
        spec.get("x_label", ""), spec.get("y_label", ""),
        W, H, ML, MR, MT, MB,
        grid=spec.get("grid", True)
    )

    # ── Lines (clipped to axis range)
    for ln in spec["lines"]:
        x1 = to_x(ln["x1"])
        y1 = to_y(ln["y1"])
        x2 = to_x(ln["x2"])
        y2 = to_y(ln["y2"])
        dash = 'stroke-dasharray="6,4"' if ln.get("dashed") else ""
        els.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                   f'stroke="black" stroke-width="{SW}" {dash}/>')
        if ln.get("label"):
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            els.append(_txt(mx + 8, my, ln["label"],
                            anchor="start", size=FS_SM))

    for pt in spec.get("points", []):
        x = to_x(pt["x"])
        y = to_y(pt["y"])
        els.append(_circ(x, y, DOT_R, fill="black"))
        if pt.get("label"):
            els.append(_txt(x + 8, y - 6, pt["label"],
                            anchor="start", size=FS_SM))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. SLOPE TRIANGLE
# ═══════════════════════════════════════════════════════════════════════════════

def render_slope_triangle(spec: dict) -> str:
    """
    Spec keys:
      Same as linear_graph plus:
      slope_triangle  dict  {x_start, x_end, y_start, y_end,
                             run_label (optional), rise_label (optional)}
    """
    _req(spec, "x_min", "x_max", "y_min", "y_max",
         "lines", "slope_triangle")

    # Render base linear graph first
    base_svg = render_linear_graph(spec)

    # Parse to extract body and re-render with slope triangle added
    W  = int(spec.get("width", 360))
    H  = int(spec.get("height", 360))
    ML = 50
    MR = 24
    MT = 24
    MB = 44
    x_int = float(spec.get("x_interval", 1))
    y_int = float(spec.get("y_interval", 1))

    els, to_x, to_y = _coord_plane_base(
        float(spec["x_min"]), float(spec["x_max"]), x_int,
        float(spec["y_min"]), float(spec["y_max"]), y_int,
        spec.get("x_label", ""), spec.get("y_label", ""),
        W, H, ML, MR, MT, MB,
        grid=spec.get("grid", True)
    )

    for ln in spec["lines"]:
        x1, y1 = to_x(ln["x1"]), to_y(ln["y1"])
        x2, y2 = to_x(ln["x2"]), to_y(ln["y2"])
        els.append(_line(x1, y1, x2, y2, stroke_width=SW))

    # ── Slope triangle
    st  = spec["slope_triangle"]
    sx1 = to_x(st["x_start"])
    sx2 = to_x(st["x_end"])
    sy1 = to_y(st["y_start"])
    sy2 = to_y(st["y_end"])

    # Horizontal leg (run)
    els.append(_line(sx1, sy1, sx2, sy1,
                     stroke=GRAY, stroke_width=SW_THIN,
                     stroke_dasharray="5,3"))
    # Vertical leg (rise)
    els.append(_line(sx2, sy1, sx2, sy2,
                     stroke=GRAY, stroke_width=SW_THIN,
                     stroke_dasharray="5,3"))

    if st.get("run_label"):
        els.append(_txt((sx1 + sx2) / 2, sy1 + 14,
                        st["run_label"], size=FS_SM))
    if st.get("rise_label"):
        els.append(_txt(sx2 + 12, (sy1 + sy2) / 2,
                        st["rise_label"], anchor="start", size=FS_SM))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. BAR GRAPH
# ═══════════════════════════════════════════════════════════════════════════════

def render_bar_graph(spec: dict) -> str:
    """
    Spec keys:
      categories   list of str
      values       list of float
      y_min        float  default 0
      y_max        float
      y_interval   float
      x_label, y_label
      bar_width_fraction  float  default 0.6
      width, height
    """
    _req(spec, "categories", "values", "y_max")

    cats = spec["categories"]
    vals = spec["values"]
    if len(cats) != len(vals):
        raise ValueError("bar_graph: categories and values must be same length")

    W   = int(spec.get("width", 400))
    H   = int(spec.get("height", 280))
    ML  = 52
    MR  = 16
    MT  = 20
    MB  = 52
    bwf = float(spec.get("bar_width_fraction", 0.6))

    y_min = float(spec.get("y_min", 0))
    y_max = float(spec["y_max"])
    y_int = float(spec.get("y_interval", 1))

    _, to_y = make_scale(y_min, y_max, H - MB, MT)

    n      = len(cats)
    slot_w = (W - ML - MR) / n
    bar_w  = slot_w * bwf
    y0     = to_y(y_min)

    # ── Dynamic font sizes
    n_y_ticks = max(int(round((y_max - y_min) / y_int)), 1)
    fs_y      = _axis_fs(H - MT - MB, n_y_ticks, min(H, 80))   # cap so bars don't inflate font
    fs_cat    = _cell_fs(slot_w * 0.9, MB * 0.4)       # category labels: fit in slot
    sw        = _stroke_w(H)

    els = []

    # ── Y grid lines and labels
    v = y_min
    while v <= y_max + 1e-9:
        y = to_y(v)
        els.append(_line(ML, y, W - MR, y, stroke=GRAY_LT, stroke_width=0.5))
        els.append(_txt(ML - 8, y + 4, _lbl(v), anchor="end", size=fs_y))
        v = round(v + y_int, 10)

    # ── Axes
    els.append(_line(ML, MT, ML, H - MB, stroke_width=sw))
    els.append(_line(ML, y0, W - MR, y0, stroke_width=sw))

    # ── Bars
    for i, (cat, val) in enumerate(zip(cats, vals)):
        bx    = ML + i * slot_w + (slot_w - bar_w) / 2
        by    = to_y(val)
        bh    = abs(y0 - by)
        bar_y = min(y0, by)
        els.append(_rect(round(bx, 2), round(bar_y, 2),
                         round(bar_w, 2), round(bh, 2),
                         fill=GRAY_LT, stroke_width=round(sw * 0.7, 2)))
        # Category label below
        cx = bx + bar_w / 2
        els.append(_txt(round(cx, 2), H - MB + 16, cat, size=fs_cat))

    if spec.get("y_label"):
        mid_y = (MT + H - MB) / 2
        els.append(
            f'<text x="{12}" y="{round(mid_y,2)}" '
            f'font-family="{FONT}" font-size="{FS_SM}" '
            f'text-anchor="middle" fill="{GRAY}" '
            f'transform="rotate(-90 12 {round(mid_y,2)})">'
            f'{spec["y_label"]}</text>'
        )
    if spec.get("x_label"):
        els.append(_txt((ML + W - MR) / 2, H - 4,
                        spec["x_label"], size=FS_SM, fill=GRAY))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. DOT PLOT
# ═══════════════════════════════════════════════════════════════════════════════

def render_dot_plot(spec: dict) -> str:
    """
    Spec keys:
      axis_min, axis_max, labeled_interval
      dots        list of float  (values — duplicates stack vertically)
      x_label     str
      dot_radius  int  default 5
      width, height
    """
    _req(spec, "axis_min", "axis_max", "labeled_interval", "dots")

    W    = int(spec.get("width", 400))
    dr   = int(spec.get("dot_radius", 5))
    gap  = dr * 2 + 2   # vertical gap between stacked dots

    # Count stacks to determine height
    from collections import Counter
    counts = Counter(spec["dots"])
    max_stack = max(counts.values()) if counts else 0
    dot_area_h = max_stack * gap + dr + 10
    H    = int(spec.get("height", dot_area_h + 72))  # 72 = axis + tick labels + x_label

    ML   = 48
    MR   = 24
    y_ax = H - 36

    _, to_px = make_scale(spec["axis_min"], spec["axis_max"], ML, W - MR)

    els = _h_axis_elements(
        spec["axis_min"], spec["axis_max"],
        spec["labeled_interval"],
        ML, W - MR, y_ax, to_px,
        W=W, H=min(H, 80),   # cap so dot area height doesn't inflate font size
        show_arrows=False,
    )

    # ── Stack dots
    stack = {}
    for v in spec["dots"]:
        stack[v] = stack.get(v, 0) + 1
        x  = to_px(v)
        y  = y_ax - dr - (stack[v] - 1) * gap
        els.append(_circ(x, y, dr, fill="black"))

    if spec.get("x_label"):
        # Position below tick labels with proper clearance (not H-6 which overlaps)
        H_font  = min(H, 80)
        n_ticks = max(int(round((spec["axis_max"] - spec["axis_min"]) / spec["labeled_interval"])), 1)
        t_sp    = (W - ML - MR) / n_ticks
        t_font  = round(min(max(8.0, min(H_font * 0.16, t_sp * 0.45)), 22.0), 1)
        t_half  = round(min(max(3.0, H_font * 0.045), 7.0), 2)
        lbl_y   = round(y_ax + t_half + t_font * 0.75 + 3 + FS_SM + 4, 2)
        els.append(_txt(W // 2, lbl_y, spec["x_label"], size=FS_SM, fill=GRAY))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. HISTOGRAM
# ═══════════════════════════════════════════════════════════════════════════════

def render_histogram(spec: dict) -> str:
    """
    Spec keys:
      bins        list  [{min, max, frequency}]
      y_max       int   (max frequency for y axis)
      y_interval  int
      x_label, y_label
      width, height
    """
    _req(spec, "bins", "y_max")

    bins  = spec["bins"]
    W     = int(spec.get("width", 400))
    H     = int(spec.get("height", 280))
    ML    = 52
    MR    = 16
    MT    = 20
    MB    = 52

    x_min = float(bins[0]["min"])
    x_max = float(bins[-1]["max"])
    y_min = 0
    y_max = float(spec["y_max"])
    y_int = float(spec.get("y_interval", 1))

    _, to_x = make_scale(x_min, x_max, ML, W - MR)
    _, to_y = make_scale(y_min, y_max, H - MB, MT)

    # ── Dynamic font sizes
    n_bins    = len(bins)
    bin_w_px  = (W - ML - MR) / max(n_bins, 1)
    fs_x      = _cell_fs(bin_w_px, MB * 0.4)          # bin edge labels
    n_y_ticks = max(int(round(y_max / y_int)), 1)
    fs_y      = _axis_fs(H - MT - MB, n_y_ticks, W)   # y-axis labels
    sw        = _stroke_w(H)

    els = []
    y0  = to_y(0)

    # ── Y grid and labels
    v = y_min
    while v <= y_max + 1e-9:
        y = to_y(v)
        els.append(_line(ML, y, W - MR, y, stroke=GRAY_LT, stroke_width=0.5))
        els.append(_txt(ML - 8, y + 4, _lbl(v), anchor="end", size=fs_y))
        v = round(v + y_int, 10)

    # ── Axes
    els.append(_line(ML, MT, ML, H - MB, stroke_width=sw))
    els.append(_line(ML, y0, W - MR, y0, stroke_width=sw))

    # ── Bins (bars touch — no gap)
    for b in bins:
        bx  = to_x(b["min"])
        bx2 = to_x(b["max"])
        bw  = bx2 - bx
        by  = to_y(b["frequency"])
        bh  = y0 - by
        els.append(_rect(round(bx, 2), round(by, 2),
                         round(bw, 2), round(bh, 2),
                         fill=GRAY_LT, stroke_width=round(sw * 0.7, 2)))
        els.append(_txt(round(bx, 2), y0 + 16, _lbl(b["min"]), size=fs_x))
    # Last right edge
    els.append(_txt(to_x(bins[-1]["max"]), y0 + 16,
                    _lbl(bins[-1]["max"]), size=fs_x))

    if spec.get("x_label"):
        els.append(_txt((ML + W - MR) / 2, H - 4,
                        spec["x_label"], size=FS_SM, fill=GRAY))
    if spec.get("y_label"):
        mid_y = (MT + H - MB) / 2
        els.append(
            f'<text x="12" y="{round(mid_y,2)}" '
            f'font-family="{FONT}" font-size="{FS_SM}" '
            f'text-anchor="middle" fill="{GRAY}" '
            f'transform="rotate(-90 12 {round(mid_y,2)})">'
            f'{spec["y_label"]}</text>'
        )

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 23 & 24. BOX PLOT (single and comparative)
# ═══════════════════════════════════════════════════════════════════════════════

def _box_plot_elements(group: dict, y_center: float,
                       box_h: float, to_px,
                       label_x: float,
                       font_size: float = None,
                       stroke_w: float = None) -> list:
    """
    Draw one box plot row.
    group keys: label, min, q1, median, q3, max
    font_size and stroke_w can be passed by caller for dynamic scaling.
    Returns list of SVG elements.
    """
    fs = font_size or FS
    sw = stroke_w  or SW

    mn  = to_px(group["min"])
    q1  = to_px(group["q1"])
    med = to_px(group["median"])
    q3  = to_px(group["q3"])
    mx  = to_px(group["max"])

    top   = y_center - box_h / 2
    bot   = y_center + box_h / 2
    whisk = box_h * 0.4

    els = []
    els.append(_rect(round(q1, 2), round(top, 2),
                     round(q3 - q1, 2), round(box_h, 2),
                     fill="white", stroke_width=round(sw * 1.3, 2)))
    els.append(_line(med, top, med, bot, stroke_width=round(sw * 1.3, 2)))
    els.append(_line(mn, y_center, q1, y_center, stroke_width=sw))
    els.append(_line(mn, y_center - whisk, mn, y_center + whisk, stroke_width=sw))
    els.append(_line(q3, y_center, mx, y_center, stroke_width=sw))
    els.append(_line(mx, y_center - whisk, mx, y_center + whisk, stroke_width=sw))
    if group.get("label"):
        els.append(_txt(round(label_x, 2), round(y_center + 4, 2),
                        group["label"], anchor="end", size=fs))
    return els


def render_box_plot(spec: dict) -> str:
    """
    Spec keys:
      axis_min, axis_max, labeled_interval, axis_label
      min, q1, median, q3, max  (floats — ALL must land on labeled tick marks)
      label   str  optional group label
      width, height
    """
    _req(spec, "axis_min", "axis_max", "labeled_interval",
         "min", "q1", "median", "q3", "max")

    W   = int(spec.get("width", 480))
    H   = int(spec.get("height", 120))
    ML  = 60
    MR  = 20
    GAP = 20   # gap between box and axis line

    # The bottom margin must accommodate: tick marks + tick labels + axis label gap.
    # We compute the tick label height using H_font (capped at 80) so that extra canvas
    # height for the box area above doesn't inflate the font size.
    H_font = min(H, 80)
    n_ticks    = max(int(round((spec["axis_max"] - spec["axis_min"]) / spec["labeled_interval"])), 1)
    t_spacing  = (W - ML - MR) / n_ticks
    fs_ax      = round(min(max(8.0, min(H_font * 0.16, t_spacing * 0.45)), 22.0), 1)
    tick_half  = round(min(max(3.0, H_font * 0.045), 7.0), 2)
    sw         = _stroke_w(H_font)
    # Bottom margin = tick_half + label ascent + gap + (axis label height + gap if present)
    axis_lbl_h = (FS_SM + 6) if spec.get("axis_label") else 0
    MB         = round(tick_half + fs_ax * 0.75 + 4 + axis_lbl_h, 0)
    y_ax       = H - int(MB)
    label_x    = ML - 8

    _, to_px = make_scale(spec["axis_min"], spec["axis_max"], ML, W - MR)

    els = _h_axis_elements(
        spec["axis_min"], spec["axis_max"],
        spec["labeled_interval"],
        ML, W - MR, y_ax, to_px,
        W=W, H=H_font,   # cap for font sizing — box area above axis is not label space
        show_arrows=False,
    )

    group = {k: float(spec[k]) for k in ("min", "q1", "median", "q3", "max")}
    group["label"] = spec.get("label", "")

    box_h_dyn  = round(min(max(14.0, H_font * 0.18), 28.0), 1)
    box_center = y_ax - GAP - box_h_dyn // 2 - 2
    els += _box_plot_elements(group, box_center, box_h_dyn, to_px, label_x,
                              font_size=fs_ax, stroke_w=sw)

    if spec.get("axis_label"):
        # Place below tick labels with 6px clearance
        tick_lbl_bottom = y_ax + tick_half + fs_ax * 0.75 + 3
        ax_lbl = spec["axis_label"]
        ax_lbl = ax_lbl[0].upper() + ax_lbl[1:] if ax_lbl else ax_lbl
        els.append(_txt(W // 2, round(tick_lbl_bottom + 6 + FS_SM * 0.75, 2),
                        ax_lbl, size=FS_SM))

    return _wrap("\n".join(els), W, H)


def render_box_plot_comparative(spec: dict) -> str:
    """
    Spec keys:
      axis_min, axis_max, labeled_interval, axis_label
      groups  list  [{label, min, q1, median, q3, max}]
             Groups listed in order A first (top), B second (bottom).
      width, height
    """
    _req(spec, "axis_min", "axis_max", "labeled_interval", "groups")

    groups  = spec["groups"]
    n       = len(groups)
    W       = int(spec.get("width", 480))
    GAP     = 20    # gap between bottom box and axis
    BOX_H   = 22
    SPACING = 48    # vertical spacing between group centers
    ML      = 64
    MR      = 20

    # Compute font/stroke sizes using H_font=80 cap (same reason as render_box_plot)
    H_font    = 80
    n_ticks   = max(int(round((spec["axis_max"] - spec["axis_min"]) / spec["labeled_interval"])), 1)
    t_spacing = (W - ML - MR) / n_ticks
    fs_ax     = round(min(max(8.0, min(H_font * 0.16, t_spacing * 0.45)), 22.0), 1)
    tick_half = round(min(max(3.0, H_font * 0.045), 7.0), 2)
    sw        = _stroke_w(H_font)
    axis_lbl_h = (FS_SM + 6) if spec.get("axis_label") else 0
    MB        = round(tick_half + fs_ax * 0.75 + 4 + axis_lbl_h, 0)

    H       = int(spec.get("height", n * SPACING + GAP + int(MB) + 10))
    y_ax    = H - int(MB)
    label_x = ML - 8

    _, to_px = make_scale(spec["axis_min"], spec["axis_max"], ML, W - MR)

    els = _h_axis_elements(
        spec["axis_min"], spec["axis_max"],
        spec["labeled_interval"],
        ML, W - MR, y_ax, to_px,
        W=W, H=H_font,   # cap for font sizing
        show_arrows=False,
    )

    # Draw groups from bottom to top (last group lowest = Group B at bottom)
    for i, grp in enumerate(reversed(groups)):
        y_center = y_ax - GAP - BOX_H // 2 - i * SPACING
        g = {k: float(grp[k]) for k in ("min", "q1", "median", "q3", "max")}
        g["label"] = grp.get("label", "")
        els += _box_plot_elements(g, y_center, BOX_H, to_px, label_x,
                                  font_size=fs_ax, stroke_w=sw)

    if spec.get("axis_label"):
        tick_lbl_bottom = y_ax + tick_half + fs_ax * 0.75 + 3
        ax_lbl_c = spec["axis_label"]
        ax_lbl_c = ax_lbl_c[0].upper() + ax_lbl_c[1:] if ax_lbl_c else ax_lbl_c
        els.append(_txt(W // 2, round(tick_lbl_bottom + 6 + FS_SM * 0.75, 2),
                        ax_lbl_c, size=FS_SM))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. CIRCLE GRAPH (PIE CHART)
# ═══════════════════════════════════════════════════════════════════════════════

def render_circle_graph(spec: dict) -> str:
    """
    Spec keys:
      slices  list  [{label, percentage}]  (percentages should sum to 100)
      width, height
    """
    _req(spec, "slices")

    slices = spec["slices"]
    W      = int(spec.get("width", 320))
    H      = int(spec.get("height", 280))
    cx     = W // 2
    cy     = (H - 40) // 2 + 10
    r      = min(cx, cy) - 24

    # Gray shades for slices (cycle through — no color)
    fills = ["white", GRAY_LT, GRAY, "#bbb", "#ddd", "#666"]

    # ── Dynamic sizing
    # Font inside slice: chord length at label radius ~ 2 * r_label * sin(sweep/2)
    # We use the smallest slice to set a safe ceiling.
    MIN_PCT_INSIDE = 8.0   # slices smaller than this get outside labels
    n_slices       = len(slices)
    fs_legend      = _cell_fs((W - 16) / max(n_slices, 1), 20.0)
    sw_slice       = round(min(max(0.5, r * 0.01), 1.5), 2)

    els   = []
    angle = 0
    for i, sl in enumerate(slices):
        pct   = float(sl["percentage"])
        sweep = pct * 3.6

        # ── Slice path
        d   = _arc(cx, cy, r, angle, angle + sweep)
        fll = fills[i % len(fills)]
        # black border between slices + outer circle boundary
        els.append(_path(d, fill=fll, stroke="black", stroke_width=sw_slice))

        # ── Label placement: inside large slices, outside tiny ones
        mid_a = math.radians(angle + sweep / 2 - 90)

        if pct >= MIN_PCT_INSIDE:
            # Inside label: font scales with arc chord at label radius
            label_r   = r * 0.62
            chord_len = 2 * label_r * math.sin(math.radians(sweep / 2))
            fs_slice  = round(min(max(7.0, chord_len * 0.28), 14.0), 1)
            lx = round(cx + label_r * math.cos(mid_a), 2)
            ly = round(cy + label_r * math.sin(mid_a), 2)
            # Use dark text on light fills, light text on dark fills
            txt_fill = "black" if fll in ("white", GRAY_LT, "#ddd") else "white"
            els.append(_txt(lx, ly + fs_slice * 0.35, f"{_fmt(pct)}%",
                            size=fs_slice, fill=txt_fill))
        else:
            # Outside label: leader line from slice midpoint to label
            inner_r = r * 0.75
            outer_r = r * 1.15
            ix = round(cx + inner_r * math.cos(mid_a), 2)
            iy = round(cy + inner_r * math.sin(mid_a), 2)
            ox = round(cx + outer_r * math.cos(mid_a), 2)
            oy = round(cy + outer_r * math.sin(mid_a), 2)
            els.append(_line(ix, iy, ox, oy, stroke=GRAY, stroke_width=0.8))
            anchor = "start" if math.cos(mid_a) >= 0 else "end"
            els.append(_txt(ox, oy + 4, f"{_fmt(pct)}%",
                            anchor=anchor, size=9.0))

        angle = round(angle + sweep, 4)

    # ── Legend at bottom — font scales with available width per item
    leg_y  = H - 24
    leg_x  = 16
    box_sz = 10
    for i, sl in enumerate(slices):
        fll     = fills[i % len(fills)]
        lbl_txt = sl.get("label", f"Slice {i+1}")
        # Use a visible border stroke; for white fill use a darker border
        swatch_stroke = round(max(0.8, r * 0.008), 2)
        els.append(_rect(leg_x, leg_y - box_sz, box_sz, box_sz,
                         fill=fll, stroke="black", stroke_width=swatch_stroke))
        els.append(_txt(leg_x + box_sz + 4, leg_y,
                        lbl_txt, anchor="start", size=fs_legend))
        leg_x += max(50, len(lbl_txt) * fs_legend * 0.62 + box_sz + 8)

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 26. SCATTER PLOT
# ═══════════════════════════════════════════════════════════════════════════════

def render_scatter_plot(spec: dict) -> str:
    """
    Spec keys:
      x_min, x_max, x_interval, x_label
      y_min, y_max, y_interval, y_label
      points      list  [{x, y}]
      trend_line  dict  {x1, y1, x2, y2} optional
      width, height
    """
    _req(spec, "x_min", "x_max", "y_min", "y_max", "points")

    W  = int(spec.get("width", 360))
    H  = int(spec.get("height", 320))
    ML = 60   # wider left margin for rotated y-label
    MR = 24
    MT = 24
    MB = 52   # deeper bottom margin for x-label

    x_int = float(spec.get("x_interval", 1))
    y_int = float(spec.get("y_interval", 1))

    x_label = spec.get("x_label", "")
    y_label = spec.get("y_label", "")

    # Pass empty strings so _coord_plane_base draws no axis labels —
    # scatter_plot uses Image 2 style (rotated y-label, centred x-label below)
    els, to_x, to_y = _coord_plane_base(
        float(spec["x_min"]), float(spec["x_max"]), x_int,
        float(spec["y_min"]), float(spec["y_max"]), y_int,
        "", "",
        W, H, ML, MR, MT, MB,
        grid=True
    )

    # ── Trend line (if provided)
    if spec.get("trend_line"):
        tl = spec["trend_line"]
        els.append(_line(to_x(tl["x1"]), to_y(tl["y1"]),
                         to_x(tl["x2"]), to_y(tl["y2"]),
                         stroke=GRAY, stroke_width=SW_THIN,
                         stroke_dasharray="6,4"))

    # ── Data points (dot radius scales with canvas)
    dot_r = round(min(max(3.0, min(W, H) * 0.012), 6.0), 1)
    for pt in spec["points"]:
        x = to_x(pt["x"])
        y = to_y(pt["y"])
        els.append(_circ(x, y, dot_r, fill="black"))

    # ── Axis labels — Image 2 style
    # x-label: centred horizontally below the plot, inside bottom margin
    if x_label:
        els.append(_txt((ML + W - MR) / 2, H - 8,
                        x_label, anchor="middle", size=FS_SM, fill=GRAY))
    # y-label: rotated 90°, centred vertically on the left side of the plot
    if y_label:
        mid_y = (MT + H - MB) / 2
        els.append(
            f'<text x="14" y="{round(mid_y, 2)}" '
            f'font-family="{FONT}" font-size="{FS_SM}" '
            f'text-anchor="middle" fill="{GRAY}" '
            f'transform="rotate(-90 14 {round(mid_y, 2)})">'
            f'{y_label}</text>'
        )

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 27. TWO-WAY FREQUENCY TABLE  (returns HTML, not SVG)
# ═══════════════════════════════════════════════════════════════════════════════

def render_two_way_table(spec: dict) -> str:
    """
    Returns an HTML <table> string (not SVG).
    The pipeline detects this and inserts it directly as HTML.

    Spec keys:
      row_header    str   e.g. "Grade"
      col_header    str   e.g. "Preference"
      row_labels    list of str
      col_labels    list of str
      values        list of list  (rows × cols)
      show_totals   bool  default False
    """
    _req(spec, "row_labels", "col_labels", "values")

    rows    = spec["row_labels"]
    cols    = spec["col_labels"]
    vals    = spec["values"]
    row_hdr = spec.get("row_header", "")
    col_hdr = spec.get("col_header", "")
    totals  = spec.get("show_totals", False)

    sty = (
        'style="border-collapse:collapse;font-family:Arial,sans-serif;'
        'font-size:13px;max-width:480px"'
    )
    td_sty  = 'style="border:1px solid #ccc;padding:6px 12px;text-align:center"'
    th_sty  = ('style="border:1px solid #ccc;padding:6px 12px;'
               'background:#f0f0f0;font-weight:600;text-align:center"')
    hdr_sty = ('style="border:1px solid #ccc;padding:6px 12px;'
               'background:#f0f0f0;font-weight:600;text-align:left"')

    lines = [f'<table {sty}>']

    # ── Header row
    lines.append(f'<tr><th {hdr_sty}>{row_hdr} / {col_hdr}</th>')
    for c in cols:
        lines.append(f'<th {th_sty}>{c}</th>')
    if totals:
        lines.append(f'<th {th_sty}>Total</th>')
    lines.append('</tr>')

    # ── Data rows
    for ri, row_lbl in enumerate(rows):
        lines.append(f'<tr><th {hdr_sty}>{row_lbl}</th>')
        row_total = 0
        for ci in range(len(cols)):
            v = vals[ri][ci]
            row_total += v
            lines.append(f'<td {td_sty}>{v}</td>')
        if totals:
            lines.append(f'<td {th_sty}>{row_total}</td>')
        lines.append('</tr>')

    # ── Column totals row
    if totals:
        lines.append(f'<tr><th {hdr_sty}>Total</th>')
        grand = 0
        for ci in range(len(cols)):
            col_sum = sum(vals[ri][ci] for ri in range(len(rows)))
            grand += col_sum
            lines.append(f'<th {th_sty}>{col_sum}</th>')
        lines.append(f'<th {th_sty}>{grand}</th>')
        lines.append('</tr>')

    lines.append('</table>')
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# 28. PLACE VALUE CHART
# ═══════════════════════════════════════════════════════════════════════════════

def render_place_value_chart(spec: dict) -> str:
    """
    Spec keys:
      columns   list of str  e.g. ["Thousands","Hundreds","Tens","Ones"]
      values    list of int  one value per column
      width, height
    """
    _req(spec, "columns", "values")

    cols = spec["columns"]
    vals = spec["values"]
    if len(cols) != len(vals):
        raise ValueError("place_value_chart: columns and values must be same length")

    n      = len(cols)
    W      = int(spec.get("width", max(320, n * 80)))
    H      = int(spec.get("height", 110))
    ML     = 8
    MR     = 8
    col_w  = (W - ML - MR) / n
    hdr_h  = 36    # taller header row so text has more room
    val_h  = H - hdr_h - 16

    # ── Dynamic font sizes
    # Both derive from col_w so header and value are proportionally similar.
    # Header uses slightly smaller multiplier because text is typically longer.
    fs_val = _cell_fs(col_w * 0.75, val_h * 0.55)   # digit value
    fs_hdr = _cell_fs(col_w * 0.65, hdr_h)           # column header (full height, not halved)
    sw     = _stroke_w(H)

    els    = []

    # ── Column headers and value cells
    for i, (col, val) in enumerate(zip(cols, vals)):
        x = ML + i * col_w
        # Header
        els.append(_rect(round(x, 2), 8, round(col_w, 2), hdr_h,
                         fill=GRAY_LT, stroke_width=round(sw * 0.7, 2)))
        els.append(_txt(round(x + col_w / 2, 2), 8 + hdr_h / 2 + fs_hdr * 0.35,
                        col, size=fs_hdr))
        # Value cell
        els.append(_rect(round(x, 2), 8 + hdr_h, round(col_w, 2), val_h,
                         fill="white", stroke_width=round(sw * 0.7, 2)))
        els.append(_txt(round(x + col_w / 2, 2),
                        8 + hdr_h + val_h / 2 + fs_val * 0.35,
                        str(val), size=fs_val))

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 29. LABELED RECTANGULAR PRISM (oblique projection)
# ═══════════════════════════════════════════════════════════════════════════════

def render_rectangular_prism_labeled(spec: dict) -> str:
    """
    Spec keys:
      length_value  float  (horizontal, front face width)
      width_value   float  (depth, goes back-right at 45°)
      height_value  float  (vertical)
      unit          str
      width, height (SVG canvas)

    Uses cabinet oblique projection:
      - Front face: normal rectangle
      - Depth: at 45°, scaled 0.5× (standard cabinet proportion)
    """
    _req(spec, "length_value", "width_value", "height_value")

    lv,  l_lbl_val = _unpack(spec["length_value"])
    wv,  w_lbl_val = _unpack(spec["width_value"])
    hv,  h_lbl_val = _unpack(spec["height_value"])
    unit = spec.get("unit", "")
    W    = int(spec.get("width", 320))
    H    = int(spec.get("height", 260))

    # ── Scale all three dimensions to fit in canvas
    pad      = 60
    avail_w  = W - 2 * pad
    avail_h  = H - 2 * pad

    # Cabinet oblique: depth offset = depth * 0.5 at 45°
    depth_frac = 0.5
    angle_rad  = math.radians(45)
    ox = depth_frac * math.cos(angle_rad)   # x offset per unit of depth
    oy = depth_frac * math.sin(angle_rad)   # y offset per unit of depth (upward)

    # Fit: total projected width = lv + wv * ox, total height = hv + wv * oy
    proj_w = lv + wv * ox
    proj_h = hv + wv * oy

    scale_f = min(avail_w / proj_w, avail_h / proj_h)

    L  = lv * scale_f               # front face width (px)
    H2 = hv * scale_f               # front face height (px)
    dx = wv * ox * scale_f           # depth x-offset (px)
    dy = wv * oy * scale_f           # depth y-offset (px)

    # Anchor: front face bottom-left corner
    bx = (W - L - dx) / 2
    by = (H - H2 - dy) / 2 + H2 + dy   # bottom of front face

    # 8 vertices:
    # Front face: FL (front-left-bottom), FR, FRT (front-right-top), FLT
    FL  = (round(bx, 2),       round(by, 2))
    FR  = (round(bx + L, 2),   round(by, 2))
    FRT = (round(bx + L, 2),   round(by - H2, 2))
    FLT = (round(bx, 2),       round(by - H2, 2))

    # Back face (offset by dx, -dy)
    BL  = (round(bx + dx, 2),       round(by - dy, 2))
    BR  = (round(bx + L + dx, 2),   round(by - dy, 2))
    BRT = (round(bx + L + dx, 2),   round(by - H2 - dy, 2))
    BLT = (round(bx + dx, 2),       round(by - H2 - dy, 2))

    els = []

    # ── Faces (draw back then front so front overlaps)
    # Top face
    els.append(_polygon([FLT, FRT, BRT, BLT], fill=GRAY_LT, stroke_width=SW))
    # Right face
    els.append(_polygon([FR, BR, BRT, FRT], fill=GRAY_LT, stroke_width=SW))
    # Front face
    els.append(_polygon([FL, FR, FRT, FLT], fill="white", stroke_width=SW))

    # ── Length label (bottom of front face, below with clearance)
    lbl_l = f"{l_lbl_val} {unit}".strip()
    els.append(_txt(round((FL[0] + FR[0]) / 2, 2),
                    round(by + LABEL_PAD, 2), lbl_l, size=FS))

    # ── Height label (left side, rotated)
    lbl_h = f"{h_lbl_val} {unit}".strip()
    mx = round(bx - LABEL_PAD, 2)
    my = round((by + by - H2) / 2, 2)
    els.append(
        f'<text x="{mx}" y="{my}" font-family="{FONT}" font-size="{FS}" '
        f'text-anchor="middle" fill="black" '
        f'transform="rotate(-90 {mx} {my})">{lbl_h}</text>'
    )

    # ── Width (depth) label: parallel to the depth edge (FRT→BRT), offset outward
    lbl_w = f"{w_lbl_val} {unit}".strip()
    # Midpoint of the depth edge (top-right diagonal)
    emx   = (FRT[0] + BRT[0]) / 2
    emy   = (FRT[1] + BRT[1]) / 2
    # Edge direction vector (FRT → BRT)
    edx   = BRT[0] - FRT[0]
    edy   = BRT[1] - FRT[1]
    elen  = math.hypot(edx, edy) or 1
    # Outward normal: rotate edge direction 90° clockwise → (edy, -edx)
    # Normalised and scaled by LABEL_PAD offset
    OFFSET = LABEL_PAD * 0.8
    nx_out = (edy / elen) * OFFSET
    ny_out = (-edx / elen) * OFFSET
    lx_d  = round(emx + nx_out, 2)
    ly_d  = round(emy + ny_out, 2)
    # Rotation angle to align text with the edge
    rot_d = round(math.degrees(math.atan2(edy, edx)), 1)
    els.append(
        f'<text x="{lx_d}" y="{ly_d}" '
        f'font-family="{FONT}" font-size="{FS}" text-anchor="middle" fill="black" '
        f'transform="rotate({rot_d} {lx_d} {ly_d})">{lbl_w}</text>'
    )

    return _wrap("\n".join(els), W, H)


# ═══════════════════════════════════════════════════════════════════════════════
# 30. UNIT CUBE ISOMETRIC — stacked unit cubes (Grade 5 volume)
# ═══════════════════════════════════════════════════════════════════════════════

def render_unit_cube_isometric(spec: dict) -> str:
    """
    Renders a set of unit cubes in oblique projection.
    Ported from the standalone stacked_cubes script — no svgwrite dependency,
    pure SVG string output.

    Spec keys:
      cubes       list  [[x, y, z], ...]  grid positions of each cube
                        x = left→right, y = front→back, z = bottom→top
      cube_size   int   pixel size of one cube face (default 40)
      depth_dx    int   x-offset per unit of depth (default 14)
      depth_dy    int   y-offset per unit of depth (default 14)
      edge_width  float stroke width for cube edges (default 1.5)
      padding     int   canvas padding around the figure (default 16)
      width       int   SVG width  (auto-computed from geometry if omitted)
      height      int   SVG height (auto-computed from geometry if omitted)

    Face shading (black/white/gray only — no color):
      Top face   : lightest  (#f0f0f0) — most light hits here
      Front face : medium    (#d0d0d0)
      Right face : darkest   (#b0b0b0) — in shadow
    """
    _req(spec, "cubes")

    cube_set = {tuple(c) for c in spec["cubes"]}
    cs   = int(spec.get("cube_size", 40))
    ddx  = int(spec.get("depth_dx", 14))
    ddy  = int(spec.get("depth_dy", 14))
    ew   = float(spec.get("edge_width", 1.5))
    pad  = int(spec.get("padding", 16))

    # Face shading
    TOP_FILL   = "#f0f0f0"
    FRONT_FILL = "#d0d0d0"
    RIGHT_FILL = "#b0b0b0"

    # ── Project 3D grid → 2D screen (same formula as the reference script)
    def proj(x, y, z):
        sx = x * cs + y * ddx
        sy = -z * cs - y * ddy
        return (sx, sy)

    def cube_verts(x, y, z):
        A = proj(x,     y,     z)
        B = proj(x + 1, y,     z)
        C = proj(x + 1, y,     z + 1)
        D = proj(x,     y,     z + 1)
        E = proj(x,     y + 1, z)
        F = proj(x + 1, y + 1, z)
        G = proj(x + 1, y + 1, z + 1)
        H = proj(x,     y + 1, z + 1)
        return A, B, C, D, E, F, G, H

    # ── Collect visible faces
    faces = []
    for (x, y, z) in cube_set:
        A, B, C, D, E, F, G, H = cube_verts(x, y, z)

        # Front face: visible if no cube directly in front (y - 1)
        if (x, y - 1, z) not in cube_set:
            faces.append({
                "fill": FRONT_FILL,
                "depth": (y, z, x),
                "type":  "front",
                "pts":   [A, B, C, D],
            })

        # Right face: visible if no cube to the right (x + 1)
        if (x + 1, y, z) not in cube_set:
            faces.append({
                "fill": RIGHT_FILL,
                "depth": (y, z, x),
                "type":  "right",
                "pts":   [B, F, G, C],
            })

        # Top face: visible if no cube above (z + 1)
        if (x, y, z + 1) not in cube_set:
            faces.append({
                "fill": TOP_FILL,
                "depth": (y, z, x),
                "type":  "top",
                "pts":   [D, C, G, H],
            })

    if not faces:
        raise ValueError("unit_cube_isometric: no visible faces — cubes list may be empty")

    # ── Depth sort (painter's algorithm): back→front so front faces overdraw back
    face_priority = {"right": 0, "front": 1, "top": 2}
    faces.sort(key=lambda f: (
        -f["depth"][0],          # furthest y (back) first
         f["depth"][2],          # lower x first
         f["depth"][1],          # lower z first
         face_priority[f["type"]]
    ))

    # ── Compute bounding box from all projected points
    all_pts = [pt for f in faces for pt in f["pts"]]
    min_sx = min(p[0] for p in all_pts)
    max_sx = max(p[0] for p in all_pts)
    min_sy = min(p[1] for p in all_pts)
    max_sy = max(p[1] for p in all_pts)

    W = int(spec.get("width",  int(max_sx - min_sx + 2 * pad)))
    H = int(spec.get("height", int(max_sy - min_sy + 2 * pad)))

    # ── Shift all points into positive canvas space
    ox = -min_sx + pad   # x offset
    oy = -min_sy + pad   # y offset

    def shift(pts):
        return [(round(x + ox, 2), round(y + oy, 2)) for x, y in pts]

    for f in faces:
        f["pts"] = shift(f["pts"])

    els = []

    # ── Draw face fills (back→front order already sorted)
    for f in faces:
        els.append(_polygon(f["pts"], fill=f["fill"], stroke="none"))

    # ── Collect unique edges across all faces and draw once on top
    # This produces clean edges with no double-stroke artifacts —
    # the same deduplication used in the reference script.
    def norm_edge(p1, p2):
        return tuple(sorted((p1, p2)))

    edge_set = set()
    for f in faces:
        pts = f["pts"]
        for i in range(len(pts)):
            edge_set.add(norm_edge(pts[i], pts[(i + 1) % len(pts)]))

    for (p1, p2) in edge_set:
        els.append(_line(p1[0], p1[1], p2[0], p2[1],
                         stroke_width=ew, stroke_linecap="butt"))

    return _wrap("\n".join(els), W, H)



# ═══════════════════════════════════════════════════════════════════════════════


# ─── Stem-and-leaf plot ──────────────────────────────────────────────────────

def render_stem_leaf(spec: dict) -> str:
    """
    Spec keys:
      stems    list  [{value, leaves}]  value=str/int, leaves=str "2 4 6 8"
      title    str   optional
      key      str   optional  e.g. "7|4 means 74"
      width, height
    """
    _req(spec, "stems")
    stems   = spec["stems"]
    title   = str(spec.get("title", "")).strip()
    key     = str(spec.get("key",   "")).strip()
    FONT    = 'font-family="Lato, Arial, sans-serif"'
    FS      = 13
    ML      = 20;  MR = 15;  ROW_H = 22;  LEAF_SPC = 14
    STEM_W  = 30
    SEP_X   = ML + STEM_W + 6
    LEAF_X  = SEP_X + 10

    max_n   = max((len(str(s.get("leaves","")).split()) for s in stems), default=0)
    W       = int(spec.get("width", max(220, LEAF_X + max(max_n*LEAF_SPC, 40) + MR)))
    title_h = 20 if title else 0
    key_h   = 20 if key   else 0
    H       = int(spec.get("height", 8 + title_h + 20 + len(stems)*ROW_H + key_h + 10))

    els = []
    y   = 8

    if title:
        y += 16
        els.append(f'<text x="{W//2}" y="{y}" text-anchor="middle" '
                   f'{FONT} font-size="13" font-weight="bold">{title}</text>')
        y += 6

    hdr_y = y + 14
    els.append(f'<text x="{SEP_X-4}" y="{hdr_y}" text-anchor="end" '
               f'{FONT} font-size="11" font-weight="bold" fill="{GRAY}">Stem</text>')
    els.append(f'<text x="{LEAF_X}" y="{hdr_y}" text-anchor="start" '
               f'{FONT} font-size="11" font-weight="bold" fill="{GRAY}">Leaf</text>')
    els.append(f'<line x1="{ML}" y1="{hdr_y+3}" x2="{W-MR}" y2="{hdr_y+3}" '
               f'stroke="{GRAY_LT}" stroke-width="1"/>')
    y = hdr_y + 6

    row_top = y
    row_bot = y + len(stems) * ROW_H
    els.append(f'<line x1="{SEP_X}" y1="{row_top-2}" x2="{SEP_X}" y2="{row_bot}" '
               f'stroke="black" stroke-width="1.5"/>')

    for s in stems:
        y += ROW_H
        sv     = str(s.get("value", ""))
        leaves = str(s.get("leaves", "")).split()
        els.append(f'<text x="{SEP_X-6}" y="{y}" text-anchor="end" '
                   f'{FONT} font-size="{FS}">{sv}</text>')
        for j, lf in enumerate(leaves):
            els.append(f'<text x="{LEAF_X + j*LEAF_SPC}" y="{y}" '
                       f'text-anchor="start" {FONT} font-size="{FS}">{lf}</text>')

    if key:
        y += 18
        els.append(f'<text x="{W//2}" y="{y}" text-anchor="middle" '
                   f'{FONT} font-size="10" font-style="italic" fill="{GRAY}">'
                   f'Key: {key}</text>')

    return _wrap("\n".join(els), W, H)


# ─── Panel comparison helpers ────────────────────────────────────────────────

def _panel_to_histogram(p):
    axis_min = float(p.get("axis_min", 0))
    axis_max = float(p.get("axis_max", 100))
    counts   = [int(x) for x in str(p.get("bin_counts","")).split() if x.strip()]
    if not counts:
        raise ValueError("histogram panel requires bin_counts")
    interval = (axis_max - axis_min) / len(counts)
    bins = [{"min": axis_min + i*interval,
             "max": axis_min + (i+1)*interval,
             "frequency": c} for i, c in enumerate(counts)]
    return {"type": "histogram", "bins": bins,
            "y_max":     int(p.get("y_max", 6)),
            "y_interval":int(p.get("y_interval", 2)),
            "x_label":   str(p.get("axis_label", "")),
            "y_label":   str(p.get("y_label", "Frequency"))}

def _panel_to_stem_leaf(p):
    stems = []
    for tok in str(p.get("rows","")).split():
        if ":" in tok:
            sv, lp = tok.split(":", 1)
            stems.append({"value": sv, "leaves": lp.replace(",", " ")})
    return {"type": "stem_leaf", "stems": stems, "key": str(p.get("key", ""))}

def _panel_to_circle_graph(p):
    slices = []
    for tok in str(p.get("slices","")).split():
        if ":" in tok:
            lbl, pct = tok.rsplit(":", 1)
            slices.append({"label": lbl.replace("_"," "), "percentage": float(pct)})
    return {"type": "circle_graph", "slices": slices}

_PANEL_PARSERS = {
    "histogram":    _panel_to_histogram,
    "stem_leaf":    _panel_to_stem_leaf,
    "circle_graph": _panel_to_circle_graph,
}


# ─── Panel comparison renderer ───────────────────────────────────────────────

def render_panel_comparison(spec: dict) -> str:
    """
    Render 2 or 3 graphs side by side.
    Spec keys:
      panels       list  [{type, title, ...compact-panel fields}]
      panel_count  int   (default: len(panels), max 3)
    Compact panel formats:
      histogram   — axis_min, axis_max, y_max, y_interval, axis_label,
                    bin_counts (space-separated counts, one per bin)
      stem_leaf   — rows ("5:4 6:7 7:2,4,6,8"), key
      circle_graph — slices ("label1:pct1 label2:pct2")
      Other registered types — pass fields through directly.
    """
    import re as _re
    panels = spec.get("panels", [])
    n      = min(int(spec.get("panel_count", len(panels))), 3)
    if n < 1:
        raise ValueError("panel_comparison requires at least 1 panel")

    MAX_W   = 476;  GAP = 12;  PAD = 4
    TITLE_H = 18;   P_TOP = 6
    panel_h = 250 if n == 2 else 200
    panel_w = (MAX_W - 2*PAD - (n-1)*GAP) // n
    total_w = 2*PAD + n*panel_w + (n-1)*GAP
    total_h = P_TOP + TITLE_H + panel_h + 6
    FONT    = 'font-family="Lato, Arial, sans-serif"'

    els = []
    for i, panel in enumerate(panels[:n]):
        ptype  = str(panel.get("type", ""))
        ptitle = str(panel.get("title", f"Graph {chr(65+i)}"))
        x_off  = PAD + i*(panel_w + GAP)

        els.append(
            f'<text x="{x_off + panel_w//2}" y="{P_TOP+13}" '
            f'text-anchor="middle" {FONT} font-size="14" font-weight="bold">'
            f'{ptitle}</text>')
        els.append(
            f'<rect x="{x_off}" y="{P_TOP+TITLE_H}" '
            f'width="{panel_w}" height="{panel_h}" '
            f'fill="white" stroke="{GRAY_LT}" stroke-width="1" rx="2"/>')

        try:
            if ptype == "panel_comparison":
                raise ValueError("nested panel_comparison not supported")
            if ptype in _PANEL_PARSERS:
                sub_spec = _PANEL_PARSERS[ptype](panel)
            else:
                sub_spec = {k: v for k, v in panel.items()
                            if k not in ("type","title")}
                sub_spec["type"] = ptype
            # Pass panel dimensions so sub-renderers generate native-size SVGs.
            # This prevents scaling inside the nested <svg>, which would shrink fonts.
            sub_spec["width"]  = panel_w - 8
            sub_spec["height"] = panel_h - 8
            fn = RENDERERS.get(ptype)
            if fn is None:
                raise ValueError(f"unregistered type '{ptype}'")
            if ptype in HTML_RENDERERS:
                raise ValueError("HTML renderers cannot be used as panels")
            sub_svg  = fn(sub_spec)
            vb_m     = _re.search(r'viewBox="([^"]*)"', sub_svg)
            cnt_m    = _re.search(r'<svg[^>]*>(.*)</svg>', sub_svg, _re.DOTALL)
            view_box = vb_m.group(1)  if vb_m  else "0 0 320 240"
            inner    = cnt_m.group(1) if cnt_m else ""
            # Dimensions now match sub-SVG natively — no scaling, no font shrinkage
            els.append(f'<svg x="{x_off+2}" y="{P_TOP+TITLE_H+2}" '
                       f'width="{panel_w-4}" height="{panel_h-4}" '
                       f'viewBox="{view_box}">')
            els.append(inner)
            els.append("</svg>")
        except Exception as exc:
            mid_y = P_TOP + TITLE_H + panel_h//2
            els.append(
                f'<text x="{x_off+panel_w//2}" y="{mid_y}" '
                f'text-anchor="middle" {FONT} font-size="10" fill="#c00">'
                f'[{ptype}: {str(exc)[:50]}]</text>')

        if i < n-1:
            dx = x_off + panel_w + GAP//2
            els.append(f'<line x1="{dx}" y1="{P_TOP+TITLE_H}" '
                       f'x2="{dx}" y2="{P_TOP+TITLE_H+panel_h}" '
                       f'stroke="{GRAY_LT}" stroke-width="1" stroke-dasharray="4,3"/>')

    return _wrap("\n".join(els), total_w, total_h)

RENDERERS: dict[str, Any] = {
    # Number lines
    "number_line_h":            render_number_line_h,
    "number_line_h_arrow":      render_number_line_h_arrow,
    "number_line_inequality":   render_number_line_inequality,
    "number_line_v":            render_number_line_v,
    "double_number_line":       render_double_number_line,
    # Fraction / ratio models
    "fraction_strip":           render_fraction_strip,
    "tape_diagram":             render_tape_diagram,
    "area_model_fraction":      render_area_model_fraction,
    "area_model_multiplication": render_area_model_multiplication,
    # Arrays
    "array":                    render_array,
    # Geometry — 2D
    "rectangle":                render_rectangle,
    "parallelogram":            render_parallelogram,
    "triangle":                 render_triangle,
    "circle":                   render_circle,
    "right_triangle":           render_right_triangle,
    # Coordinate plane
    "coordinate_q1":            render_coordinate_q1,
    "coordinate_4q":            render_coordinate_4q,
    "linear_graph":             render_linear_graph,
    "slope_triangle":           render_slope_triangle,
    # Data displays
    "stem_leaf":                render_stem_leaf,
    "panel_comparison":         render_panel_comparison,
    "bar_graph":                render_bar_graph,
    "dot_plot":                 render_dot_plot,
    "histogram":                render_histogram,
    "box_plot":                 render_box_plot,
    "box_plot_comparative":     render_box_plot_comparative,
    "circle_graph":             render_circle_graph,
    "scatter_plot":             render_scatter_plot,
    "two_way_table":            render_two_way_table,   # returns HTML
    # Measurement
    "place_value_chart":        render_place_value_chart,
    "rectangular_prism_labeled": render_rectangular_prism_labeled,
    # 3D
    "unit_cube_isometric":      render_unit_cube_isometric,
}

# Types that return HTML instead of SVG
HTML_RENDERERS = {"two_way_table"}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DISPATCH
# ═══════════════════════════════════════════════════════════════════════════════

def render_visual(spec_dict: dict) -> tuple:
    """
    Dispatch to the correct renderer.

    Returns
    -------
    (output, strategy)
      output   : SVG string, HTML string, or None
      strategy : 'database' | 'database_html' | 'fallback'

    The pipeline handles the difference between SVG and HTML outputs.
    Unknown types return (None, 'fallback') — pipeline uses Option A or B.
    """
    vtype = spec_dict.get("type", "").strip()
    if vtype not in RENDERERS:
        return None, "fallback"

    try:
        output = RENDERERS[vtype](spec_dict)
    except Exception as e:
        raise ValueError(f"Renderer '{vtype}' failed: {e}") from e

    if vtype in HTML_RENDERERS:
        return output, "database_html"
    return output, "database"


def list_types() -> list[str]:
    """Return all registered type keys."""
    return sorted(RENDERERS.keys())
