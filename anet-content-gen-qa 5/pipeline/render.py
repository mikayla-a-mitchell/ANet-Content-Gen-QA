"""
pipeline/render.py
===================
Phase 3 of the anet-exit-ticket-studio pipeline: parse an EXIT_TICKET XML
block, render each question's visual, and build the final HTML preview. No
Anthropic API calls happen here — this is pure parsing + rendering, ported
essentially verbatim from the team's proven `ETGenerator/app.py`
(`_parse_exit_ticket`, `_parse_visual_spec`, `_resolve_visuals`,
`_render_question_html`, `_build_html`, `KATEX_HEAD`, `SHARED_CSS`).

Two adaptations on top of that reference implementation:

1. **PNG export.** `resolve_visuals()` (ETGenerator's `_resolve_visuals`)
   additionally calls `png_export.svg_to_png_bytes()` to save a `.png` next
   to each `.svg`, when `png_export.png_available()` is true, and records
   whether a PNG exists on each question dict (`question["png_path"]`) so
   the Streamlit UI can offer a PNG download button only when one exists.
2. **Round-trip XML.** `parse_exit_ticket()` additionally captures each
   question's raw, unmodified `<VISUAL>...</VISUAL>` block text (including
   its original CDATA-wrapped SVG, if any) so `build_exit_ticket_xml()` can
   re-serialize a question after a user edits its text fields (stem, prompt,
   choices, rationales) in the in-app editor without needing to regenerate
   or re-escape the visual — visuals are never edited in this app, only
   passed through unchanged.

Free of Streamlit imports by design, so it can be exercised independently
of the running app.
"""

from __future__ import annotations

import datetime
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

# ── Make the project root importable regardless of how this module is
#    loaded (streamlit run app.py, a test script, python -m, etc.) so
#    `import png_export` and the importlib load of visual_renderers.py
#    below always resolve. ───────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import png_export  # noqa: E402  (root-level module, see path setup above)

# ── Import visual_renderers.py the same way ETGenerator does: via
#    importlib.util from its file path, since there's no package structure
#    around it. ──────────────────────────────────────────────────────────────
import importlib.util as _ilu  # noqa: E402

_RENDERERS_FILE = _ROOT / "visual_renderers.py"
_spec = _ilu.spec_from_file_location("visual_renderers", _RENDERERS_FILE)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
render_visual = _mod.render_visual


# ── XML parsing (ported from ETGenerator's _parse_exit_ticket) ────────────────
def parse_exit_ticket(xml_string: str) -> tuple:
    """Parse EXIT_TICKET XML into (lesson dict, questions list). Each
    question dict also carries `_raw_visual_block` — the original, verbatim
    <VISUAL>...</VISUAL> text (or None) — for use by build_exit_ticket_xml()
    when re-serializing after an in-app edit."""
    # Model output can contain a bare '<' as content (an answer choice of
    # "\\(<\\)" in a comparison item), which is not well-formed XML. Repair
    # on read as well as on write, so a file saved before that was handled
    # still renders instead of needing to be regenerated.
    from .validate import sanitize_item_xml
    xml_string = sanitize_item_xml(xml_string)

    svg_map = {}
    raw_visual_map = {}
    for q_m in re.finditer(r'<QUESTION id="(\d+)">(.*?)</QUESTION>', xml_string, re.DOTALL):
        qid, qbody = q_m.group(1), q_m.group(2)
        svg_m = re.search(r"<SVG>\s*<!\[CDATA\[(.*?)\]\]>\s*</SVG>", qbody, re.DOTALL)
        if svg_m:
            svg_map[qid] = svg_m.group(1).strip()
        visual_m = re.search(r"<VISUAL>.*?</VISUAL>", qbody, re.DOTALL)
        if visual_m:
            raw_visual_map[qid] = visual_m.group(0)

    clean = re.sub(r"<SVG>\s*<!\[CDATA\[.*?\]\]>\s*</SVG>", "<SVG></SVG>",
                   xml_string, flags=re.DOTALL)

    HTML_ENTITIES = {
        "&times;": "×", "&divide;": "÷", "&middot;": "·",
        "&minus;": "−", "&plusmn;": "±", "&ne;": "≠",
        "&le;": "≤", "&ge;": "≥", "&frac12;": "½",
        "&frac14;": "¼", "&frac34;": "¾", "&frac13;": "⅓",
        "&frac23;": "⅔", "&nbsp;": " ", "&mdash;": "—", "&ndash;": "–",
    }
    for entity, char in HTML_ENTITIES.items():
        clean = clean.replace(entity, char)
    clean = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)", "&amp;", clean)
    clean = re.sub(r"<!--.*?-->", "", clean, flags=re.DOTALL)
    clean = re.sub(r"\\\\", r"\\", clean)

    try:
        root = ET.fromstring(clean)
    except ET.ParseError as e:
        row, col = e.position
        lines = clean.split("\n")
        bad_line = lines[row - 1] if row <= len(lines) else "(out of range)"
        raise ValueError(
            f"XML parse error at line {row}, col {col}: {e}\n"
            f"Offending line: {repr(bad_line)}"
        ) from e

    lesson = {
        "title":     root.findtext("LESSON/TITLE", "").strip(),
        "grade":     root.findtext("LESSON/GRADE", "").strip(),
        "standards": root.findtext("LESSON/STANDARDS", "").strip(),
    }

    questions = []
    for q_el in root.findall("QUESTION"):
        qid = q_el.get("id", "?")
        v_el = q_el.find("VISUAL")
        visual = None
        if v_el is not None:
            alt_el = v_el.find("ALT")
            alt_text = (alt_el.text or "").strip() if alt_el is not None else ""
            spec_el = v_el.find("VISUAL_SPEC")
            if spec_el is not None:
                visual = {"strategy": "database",
                          "spec_dict": _parse_visual_spec(spec_el),
                          "alt": alt_text, "svg": None, "html": None}
            elif qid in svg_map:
                visual = {"strategy": "fallback",
                          "spec_dict": None,
                          "alt": alt_text, "svg": svg_map[qid], "html": None}
            elif alt_text:
                # A visual we have only a description of — the normal case for
                # an item extracted from someone else's PDF, where the figure
                # exists but cannot be reconstructed as a spec. Keeping it as
                # a described visual matters: dropping it would leave the
                # reviewers assessing the item as though it had no figure.
                visual = {"strategy": "described",
                          "spec_dict": None,
                          "alt": alt_text, "svg": None, "html": None}
        questions.append({
            "id":         qid,
            "standard":   (q_el.findtext("STANDARD") or "").strip(),
            "stem":       (q_el.findtext("STEM") or "").strip(),
            "visual":     visual,
            "prompt":     (q_el.findtext("PROMPT") or "").strip(),
            "choices":    [{"label": c.get("label"), "text": (c.text or "").strip()}
                           for c in q_el.findall("CHOICES/CHOICE")],
            "correct":    (q_el.findtext("CORRECT") or "").strip(),
            "rationales": [{"label": r.get("label"), "text": (r.text or "").strip()}
                           for r in q_el.findall("RATIONALES/RATIONALE")],
            "png_path":   None,
            "_raw_visual_block": raw_visual_map.get(qid),
        })
    return lesson, questions


def _parse_visual_spec(spec_el) -> dict:
    """Parse a <VISUAL_SPEC type="..."> element into a spec dict. Ported
    verbatim from ETGenerator."""
    vtype = spec_el.get("type", "").strip()
    spec = {"type": vtype}
    raw_text = (spec_el.text or "").strip()

    joined_lines = []
    buffer, brace_depth = "", 0
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if buffer:
            buffer += " " + stripped
            brace_depth += stripped.count("[") - stripped.count("]")
            if brace_depth <= 0:
                joined_lines.append(buffer)
                buffer = ""
                brace_depth = 0
        elif ":" in stripped:
            k, _, v = stripped.partition(":")
            v = v.strip()
            open_b = v.count("[") - v.count("]")
            if open_b > 0:
                buffer = stripped
                brace_depth = open_b
            else:
                joined_lines.append(stripped)
    if buffer:
        joined_lines.append(buffer)

    UNICODE_FRACS = {
        "¼": 0.25, "½": 0.5, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3,
        "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875,
        "⅕": 0.2, "⅖": 0.4, "⅗": 0.6, "⅘": 0.8,
        "⅙": 1 / 6, "⅚": 5 / 6,
    }

    def cast(v):
        v = str(v).strip()
        try:
            return int(v)
        except Exception:
            pass
        try:
            return float(v)
        except Exception:
            pass
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        if v.lower() == "none":
            return None
        for uf, fval in UNICODE_FRACS.items():
            if v.endswith(uf):
                whole = v[:-len(uf)].strip()
                try:
                    return (int(whole) + fval, v)
                except Exception:
                    pass
        if v in UNICODE_FRACS:
            return (UNICODE_FRACS[v], v)
        mf = re.match(r"^(\d+)\s+(\d+)/(\d+)$", v)
        if mf:
            return (int(mf.group(1)) + int(mf.group(2)) / int(mf.group(3)), v)
        sf = re.match(r"^(\d+)/(\d+)$", v)
        if sf:
            return (int(sf.group(1)) / int(sf.group(2)), v)
        return v

    for line in joined_lines:
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()

        for prefix, field_name in [
            (r"group_(\d+)_(.*)", "groups"),
            (r"point_(\d+)_(.*)", "points"),
            (r"slice_(\d+)_(.*)", "slices"),
            (r"bin_(\d+)_(.*)", "bins"),
            (r"strip_(\d+)_(.*)", "strips"),
            (r"part_(\d+)_(.*)", "parts"),
            (r"line_(\d+)_(.*)", "lines"),
            (r"panel_(\d+)_(.*)", "panels"),
            (r"stem_(\d+)_(.*)", "stems"),
        ]:
            m = re.match(prefix, key)
            if m:
                idx, field = int(m.group(1)), m.group(2)
                spec.setdefault(field_name, [])
                while len(spec[field_name]) <= idx:
                    spec[field_name].append({})
                if field_name == "strips" and field == "shaded_parts":
                    spec[field_name][idx][field] = [int(x) for x in val.split(",")]
                else:
                    spec[field_name][idx][field] = cast(val)
                break
        else:
            if key == "dots" and not val.strip().startswith("["):
                spec["dots"] = [cast(v.strip()) for v in val.split(",")]
                continue
            if key in ("col_labels", "row_labels", "categories", "columns") and not val.strip().startswith("["):
                spec[key] = [v.strip() for v in val.split(",")]
                continue
            if key in ("row_parts", "col_parts") and not val.strip().startswith("["):
                spec[key] = [cast(v.strip()) for v in val.split(",")]
                continue
            if key == "values" and not val.strip().startswith("["):
                try:
                    spec[key] = [cast(v.strip()) for v in val.split(",")]
                    continue
                except Exception:
                    pass
            m = re.match(r"dot_(\d+)$", key)
            if m:
                spec.setdefault("dots", [])
                spec["dots"].append(cast(val))
                continue
            m = re.match(r"cube_(\d+)$", key)
            if m:
                spec.setdefault("cubes", [])
                spec["cubes"].append([int(x) for x in val.split(",")])
                continue
            m = re.match(r"row_label_(\d+)$", key)
            if m:
                spec.setdefault("row_labels", [])
                spec["row_labels"].append(val)
                continue
            m = re.match(r"col_label_(\d+)$", key)
            if m:
                spec.setdefault("col_labels", [])
                spec["col_labels"].append(val)
                continue
            m = re.match(r"value_(\d+)_(\d+)$", key)
            if m:
                r_idx, c_idx = int(m.group(1)), int(m.group(2))
                spec.setdefault("values", [])
                while len(spec["values"]) <= r_idx:
                    spec["values"].append([])
                while len(spec["values"][r_idx]) <= c_idx:
                    spec["values"][r_idx].append(0)
                spec["values"][r_idx][c_idx] = cast(val)
                continue
            if val.strip().startswith("["):
                import ast as _ast
                try:
                    json_like = re.sub(r"(?![\"'])\b([a-zA-Z_][\w]*)\s*:", r'"\1":', val)
                    json_like = json_like.replace("false", "False").replace("true", "True").replace("null", "None")
                    parsed = _ast.literal_eval(json_like)
                    if isinstance(parsed, list):
                        spec[key] = parsed
                        continue
                except Exception:
                    pass
            spec[key] = cast(val)
    return spec


def resolve_visuals(questions: list, visuals_dir: Path,
                     lesson_title: str, lesson_grade: str = "?") -> list:
    """Render visuals for each question; save SVGs (and, when Cairo is
    available, PNGs) to visuals_dir. Ported from ETGenerator's
    _resolve_visuals with the PNG-export adaptation described in this
    module's docstring."""
    visuals_dir = Path(visuals_dir)
    visuals_dir.mkdir(parents=True, exist_ok=True)
    log_path = visuals_dir.parent / "intermediate" / "unknown_visuals.log"
    log_lines = []
    date_str = datetime.datetime.today().strftime("%Y-%m-%d")
    png_ok = png_export.png_available()

    def _save_svg_and_png(svg_text: str, qid: str) -> tuple:
        svg_path = visuals_dir / f"q{qid}_visual.svg"
        svg_path.write_text(svg_text, encoding="utf-8")
        png_path = None
        if png_ok:
            png_bytes = png_export.svg_to_png_bytes(svg_text)
            if png_bytes:
                png_path = visuals_dir / f"q{qid}_visual.png"
                png_path.write_bytes(png_bytes)
        return svg_path, png_path

    for q in questions:
        if not q["visual"]:
            continue
        if q["visual"]["strategy"] == "database":
            spec_dict = q["visual"]["spec_dict"]
            vtype = spec_dict.get("type", "unknown")
            try:
                output, strategy = render_visual(spec_dict)
                if strategy == "fallback":
                    log_lines.append(
                        f"{date_str}  Lesson: {lesson_title}  Q{q['id']}  "
                        f"type: {vtype} -> MISSING from registry"
                    )
                    q["visual"]["strategy"] = "fallback_unregistered"
                elif strategy == "database_html":
                    q["visual"]["html"] = output
                    q["visual"]["svg"] = None
                    _log(f"    Q{q['id']} rendered as HTML table ({vtype})")
                else:
                    q["visual"]["svg"] = output
                    q["visual"]["html"] = None
                    svg_path, png_path = _save_svg_and_png(output, q["id"])
                    q["png_path"] = str(png_path) if png_path else None
                    _log(f"    Q{q['id']} rendered via Python ({vtype}) -> {svg_path.name}")
            except Exception as exc:
                _log(f"    Q{q['id']} renderer error for '{vtype}': {exc}")
                q["visual"]["strategy"] = "render_error"

        elif q["visual"]["strategy"] == "fallback":
            svg = q["visual"].get("svg")
            if svg:
                svg_path, png_path = _save_svg_and_png(svg, q["id"])
                q["png_path"] = str(png_path) if png_path else None
                _log(f"    Q{q['id']} fallback SVG saved -> {svg_path.name}")
            log_lines.append(
                f"{date_str}  Lesson: {lesson_title}  Q{q['id']}  -> fallback SVG  has_svg={bool(svg)}"
            )

    if log_lines:
        existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(existing + "\n".join(log_lines) + "\n", encoding="utf-8")

    return questions


def _log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


KATEX_HEAD = (
    '\n  <link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '  <link href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap" rel="stylesheet">\n'
    '  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">\n'
    '  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>\n'
    '  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"\n'
    '    onload="renderMathInElement(document.body,{'
    "delimiters:[{left:'\\\\(',right:'\\\\)',display:false}],throwOnError:false"
    '});"></script>'
)

SHARED_CSS = (
    "  <style>\n"
    "    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}\n"
    "    body{font-family:'Lato',Arial,sans-serif;font-size:15px;line-height:1.6;\n"
    "         color:#1a1a1a;max-width:720px;margin:0 auto;padding:40px 32px 60px}\n"
    "    .header{margin-bottom:28px}\n"
    "    .header h1{font-size:20px;font-weight:700;margin-bottom:6px}\n"
    "    .header .meta{font-size:13px;color:#666}\n"
    "    .header hr{border:none;border-top:1px solid #ddd;margin-top:16px}\n"
    "    .qblock{margin-bottom:36px;page-break-inside:avoid}\n"
    "    .qlabel{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:600;\n"
    "            color:#888;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}\n"
    "    .badge{background:#f0f0f0;border-radius:4px;padding:2px 8px;\n"
    "           font-size:11px;font-weight:500;color:#555;text-transform:none;letter-spacing:0}\n"
    "    .stem{font-size:15px;margin-bottom:10px}\n"
    "    .visual{margin:14px 0;max-width:480px}\n"
    "    .visual img,.visual svg{max-width:100%;display:block}\n"
    "    .prompt{font-size:15px;margin-bottom:14px}\n"
    "    .choices{list-style:none;display:flex;flex-direction:column;gap:10px}\n"
    "    .choice{display:flex;align-items:center;gap:12px;font-size:15px}\n"
    "    .lbl{width:26px;height:26px;border-radius:50%;background:#f5f5f5;\n"
    "         display:inline-flex;align-items:center;justify-content:center;\n"
    "         font-size:13px;font-weight:600;color:#333;flex-shrink:0}\n"
    "    .rationale-section{margin-top:16px;padding-top:12px;border-top:1px solid #ddd}\n"
    "    .rationale-label{font-size:12px;font-weight:700;color:#333;margin-bottom:8px}\n"
    "    .rationale-row{display:grid;grid-template-columns:24px 1fr 2fr;gap:8px 12px;\n"
    "                  font-size:12px;color:#444;margin-bottom:6px;align-items:start}\n"
    "    .rationale-lbl{font-weight:700;color:#333}\n"
    "    .rationale-choice{color:#333}\n"
    "    .rationale-text{color:#555}\n"
    "    .rationale-row.correct .rationale-lbl,\n"
    "    .rationale-row.correct .rationale-choice,\n"
    "    .rationale-row.correct .rationale-text{color:#1a6e2e;font-weight:600}\n"
    "    @media print{body{padding:20px;font-size:12pt}\n"
    "      .qblock{page-break-inside:avoid}\n"
    "      .badge{background:none;border:1px solid #ccc}}\n"
    "  </style>"
)


def _render_question_html(q: dict) -> str:
    L = ['<div class="qblock">', f'  <div class="qlabel">Question {q["id"]}']
    if q["standard"]:
        L.append(f'    <span class="badge">{q["standard"]}</span>')
    L.append("  </div>")
    if q["stem"]:
        L.append(f'  <div class="stem">{q["stem"]}</div>')
    if q["visual"]:
        L.append('  <div class="visual">')
        v = q["visual"]
        if v.get("html"):
            L.append(f'    {v["html"]}')
        elif v.get("svg"):
            svg = re.sub(r"<svg ", f'<svg role="img" aria-label="{v["alt"]}" ',
                         v["svg"], count=1)
            L.append(f"    {svg}")
        elif v.get("strategy") == "described" and v.get("alt"):
            L.append(f'    <figure style="border:1px dashed #b0b0b0;padding:10px 12px;'
                     f'margin:0;background:#fafafa">'
                     f'<figcaption style="font-size:12px;color:#555;font-style:italic">'
                     f'Figure (described from source — not reproduced): {v["alt"]}'
                     f'</figcaption></figure>')
        elif v.get("strategy") in ("fallback_unregistered", "render_error") and v.get("alt"):
            L.append(f'    <p style="color:#c00;font-style:italic;font-size:13px">'
                     f'⚠ Visual unavailable ({v["alt"]})</p>')
        L.append("  </div>")
    L.append(f'  <div class="prompt">{q["prompt"]}</div>')
    L.append('  <ul class="choices">')
    for c in q["choices"]:
        L.append(f'    <li class="choice"><span class="lbl">{c["label"]}</span>'
                 f'<span>{c["text"]}</span></li>')
    L.append("  </ul>")
    L.append('  <div class="rationale-section">')
    L.append('    <div class="rationale-label">Distractor Rationale</div>')
    for r in q["rationales"]:
        is_correct = r["label"] == q["correct"]
        row_cls = "rationale-row correct" if is_correct else "rationale-row"
        choice_text = next((c["text"] for c in q["choices"] if c["label"] == r["label"]), "")
        L.extend([
            f'    <div class="{row_cls}">',
            f'      <span class="rationale-lbl">{r["label"]}</span>',
            f'      <span class="rationale-choice">{choice_text}</span>',
            f'      <span class="rationale-text">{r["text"]}</span>',
            '    </div>',
        ])
    L.append("  </div>")
    L.append("</div>")
    return "\n".join(L)


def build_html(lesson: dict, questions: list) -> str:
    date_str = datetime.datetime.today().strftime("%B %d, %Y")
    blocks = "\n\n".join(_render_question_html(q) for q in questions)
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
        f'  <title>{lesson["title"]} — Exit Ticket</title>\n'
        f'{KATEX_HEAD}\n{SHARED_CSS}\n</head>\n<body>\n'
        '<div class="header">\n'
        f'  <h1>{lesson["title"]}</h1>\n'
        f'  <div class="meta">{lesson["grade"]} &nbsp;&middot;&nbsp; '
        f'{lesson["standards"]} &nbsp;&middot;&nbsp; Exit Ticket'
        f' &nbsp;&middot;&nbsp; {date_str}</div>\n  <hr>\n</div>\n'
        f'{blocks}\n</body>\n</html>'
    )


def render_lesson(fp: dict, xml_text: Optional[str] = None) -> tuple:
    """Full Phase 3: parse `xml_text` (defaults to reading
    fp['exit_ticket_final']), resolve visuals, build HTML, and write the
    HTML file. Returns (lesson, questions, html) so the caller (the
    Streamlit editor) can render/edit the parsed structure directly instead
    of re-reading the file it just wrote."""
    if xml_text is None:
        xml_text = fp["exit_ticket_final"].read_text(encoding="utf-8")
    try:
        lesson, questions = parse_exit_ticket(xml_text)
    except ValueError:
        # The app tells a person a failed phase leaves its raw response in
        # intermediate/<phase>_debug.txt. P3 has no API response to save, but
        # it does have the XML it choked on, and without it a parse failure
        # can only be diagnosed by regenerating the lesson. Save that instead,
        # under the name the app already promises.
        try:
            fp["intermediate_dir"].mkdir(parents=True, exist_ok=True)
            (fp["intermediate_dir"] / "p3_debug.xml").write_text(
                xml_text, encoding="utf-8")
        except Exception:
            pass
        raise
    questions = resolve_visuals(questions, fp["visuals_dir"], lesson["title"], lesson["grade"])
    html = build_html(lesson, questions)
    fp["html_file"].write_text(html, encoding="utf-8")
    _log(f"    HTML saved -> {fp['html_file'].name}")
    return lesson, questions, html


# ── XML round-trip (new: supports the in-app "Save edits & re-render" step) ────
def _xml_escape(s: Optional[str]) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_exit_ticket_xml(lesson: dict, questions: list) -> str:
    """Re-serialize a (possibly user-edited) lesson/questions structure back
    into well-formed EXIT_TICKET XML matching the pipeline's tag shape.
    Only STEM/PROMPT/CHOICES/CORRECT/RATIONALES are rebuilt from the dict —
    each question's VISUAL block (if any) is reinserted verbatim from
    `_raw_visual_block` (captured by parse_exit_ticket), since visuals are
    never edited in this app's editor."""
    parts = [
        "<EXIT_TICKET>",
        "",
        "<LESSON>",
        f"  <TITLE>{_xml_escape(lesson.get('title', ''))}</TITLE>",
        f"  <GRADE>{_xml_escape(lesson.get('grade', ''))}</GRADE>",
        f"  <STANDARDS>{_xml_escape(lesson.get('standards', ''))}</STANDARDS>",
        "</LESSON>",
        "",
    ]
    for q in questions:
        parts.append(f'<QUESTION id="{_xml_escape(str(q.get("id", "")))}">')
        parts.append(f'  <STANDARD>{_xml_escape(q.get("standard", ""))}</STANDARD>')
        parts.append(f'  <STEM>{_xml_escape(q.get("stem", ""))}</STEM>')
        parts.append("")
        raw_visual = q.get("_raw_visual_block")
        if raw_visual:
            parts.append(f"  {raw_visual}")
            parts.append("")
        parts.append(f'  <PROMPT>{_xml_escape(q.get("prompt", ""))}</PROMPT>')
        parts.append("")
        parts.append("  <CHOICES>")
        for c in q.get("choices", []):
            parts.append(f'    <CHOICE label="{_xml_escape(c.get("label", ""))}">'
                         f'{_xml_escape(c.get("text", ""))}</CHOICE>')
        parts.append("  </CHOICES>")
        parts.append("")
        parts.append(f'  <CORRECT>{_xml_escape(q.get("correct", ""))}</CORRECT>')
        parts.append("")
        parts.append("  <RATIONALES>")
        for r in q.get("rationales", []):
            parts.append(f'    <RATIONALE label="{_xml_escape(r.get("label", ""))}">'
                         f'{_xml_escape(r.get("text", ""))}</RATIONALE>')
        parts.append("  </RATIONALES>")
        parts.append("</QUESTION>")
        parts.append("")
    parts.append("</EXIT_TICKET>")
    return "\n".join(parts)
