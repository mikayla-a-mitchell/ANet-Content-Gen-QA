"""
pipeline/review.py
===================
Phase 2 review — the NEW step this app adds on top of what ETGenerator did.
Distinct from Phase 2c/2d (content + bias review, which are part of
*generation*, in pipeline/generation.py): this runs a second, independent
pass over an *already-approved* exit ticket, using two prompts
(`review_mathcheck.md`, `review_rubric.md`) adapted from the team's separate
`ItemReviewer` tool.

Both prompts expect each item's rendered visual (when it has one) attached
as an actual image, not just described by its ALT text — this module reads
each question's saved `.svg` (written by pipeline.render.resolve_visuals
during Phase 3) and rasterizes it to PNG via png_export.svg_to_png_bytes()
for that purpose. When Cairo isn't available in this environment, images are
simply skipped and the review relies on ALT text alone — callers should
surface `images_skipped` to the user rather than fail silently.

Free of Streamlit imports by design.
"""

from __future__ import annotations

import base64
import re
import sys as _sys
from pathlib import Path
from typing import Optional

# Make the project root importable regardless of import order (this module
# doesn't rely on pipeline.render having already been imported), so
# `import png_export` below always resolves.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))

import png_export  # noqa: E402  (root-level module, see path setup above)

from pipeline.generation import MODEL, _stream, _log  # noqa: E402

REVIEW_PROMPT_FILES = {
    "mathcheck": "review_mathcheck.md",
    "rubric": "review_rubric.md",
}

PH_EXIT_TICKET_ITEMS = "{{EXIT_TICKET_ITEMS}}"
PH_MATH_CHECK_OUTPUT = "{{MATH_CHECK_OUTPUT}}"
PH_LESSON_PROFILE = "{{LESSON_PROFILE}}"


def load_review_prompts(prompts_dir: Path) -> dict:
    prompts_dir = Path(prompts_dir)
    out = {}
    for key, filename in REVIEW_PROMPT_FILES.items():
        path = prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        out[key] = path.read_text(encoding="utf-8")
    return out


# ── Item text formatter for {{EXIT_TICKET_ITEMS}} ──────────────────────────────
def format_items_text(lesson: dict, questions: list) -> str:
    """A clean, readable text rendering of each item's stem/prompt/choices/
    correct/rationales/visual ALT. Doesn't need to match any prior tool's
    format exactly — just be readable and complete, per the review prompts'
    own framing of {{EXIT_TICKET_ITEMS}}."""
    lines = [
        f"Lesson: {lesson.get('title', '')}",
        f"Grade: {lesson.get('grade', '')}",
        f"Standards: {lesson.get('standards', '')}",
        "",
    ]
    for q in questions:
        lines.append(f"=== Item {q.get('id', '?')} ===")
        if q.get("standard"):
            lines.append(f"Standard: {q['standard']}")
        if q.get("stem"):
            lines.append(f"Stem: {q['stem']}")
        visual = q.get("visual")
        if visual:
            alt = (visual.get("alt") or "").strip()
            lines.append(f"Visual: {alt or '(visual present, no ALT description)'}")
        else:
            lines.append("Visual: none")
        lines.append(f"Prompt: {q.get('prompt', '')}")
        lines.append("Choices:")
        correct = q.get("correct", "")
        for c in q.get("choices", []):
            marker = "  <-- marked correct" if c.get("label") == correct else ""
            lines.append(f"  {c.get('label')}. {c.get('text', '')}{marker}")
        lines.append("Distractor rationales:")
        for r in q.get("rationales", []):
            lines.append(f"  {r.get('label')}: {r.get('text', '')}")
        lines.append("")
    return "\n".join(lines)


# ── Image gathering ──────────────────────────────────────────────────────────
def gather_item_images(fp: dict, questions: list) -> tuple:
    """Rasterize each question's saved .svg (from Phase 3) to PNG bytes for
    attaching to the review API calls. Returns (images, any_skipped) where
    images maps question id -> png bytes (only for items that have both a
    visual and a successfully-rasterized image), and any_skipped is True if
    at least one item's visual couldn't be attached (Cairo unavailable, or a
    conversion failure) so the caller can warn the user once."""
    images: dict = {}
    any_skipped = False
    png_ok = png_export.png_available()
    for q in questions:
        if not q.get("visual"):
            continue
        svg_path = Path(fp["visuals_dir"]) / f"q{q['id']}_visual.svg"
        if not svg_path.exists():
            # HTML-table visuals (database_html strategy) have no .svg — not
            # a failure, just nothing to attach as an image.
            continue
        if not png_ok:
            any_skipped = True
            continue
        svg_text = svg_path.read_text(encoding="utf-8")
        png_bytes = png_export.svg_to_png_bytes(svg_text)
        if png_bytes:
            images[q["id"]] = png_bytes
        else:
            any_skipped = True
    return images, any_skipped


def _build_content_with_images(prompt_text: str, questions: list, images: dict) -> list:
    content = [{"type": "text", "text": prompt_text}]
    for q in questions:
        img = images.get(q.get("id"))
        if img:
            content.append({"type": "text", "text": f"Rendered visual for Item {q['id']}:"})
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.standard_b64encode(img).decode("utf-8"),
                },
            })
    return content


# ── Phase 2 review — step 1: math check ────────────────────────────────────────
def run_math_check(fp: dict, client, prompts: dict, lesson: dict, questions: list,
                    images: Optional[dict] = None) -> str:
    """Calls review_mathcheck.md and saves the output to
    review/math_check_output.txt. `images` may be precomputed via
    gather_item_images() to avoid rasterizing twice when the caller also
    calls run_rubric_review()."""
    if images is None:
        images, _ = gather_item_images(fp, questions)

    template = prompts["mathcheck"]
    if PH_EXIT_TICKET_ITEMS not in template:
        raise ValueError(f"Placeholder not found in review_mathcheck.md: '{PH_EXIT_TICKET_ITEMS}'")
    items_text = format_items_text(lesson, questions)
    prompt_text = template.replace(PH_EXIT_TICKET_ITEMS, items_text)
    content = _build_content_with_images(prompt_text, questions, images)

    raw = _stream(client, model=MODEL, max_tokens=8000,
                  messages=[{"role": "user", "content": content}])

    text = raw.strip()
    fence_m = re.match(r"^```(?:\w+)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    if fence_m:
        text = fence_m.group(1).strip()

    if "FINAL OUTPUT" not in text.upper():
        fp["review_dir"].mkdir(parents=True, exist_ok=True)
        debug = fp["review_dir"] / "math_check_debug.txt"
        debug.write_text(raw, encoding="utf-8")
        raise ValueError(
            "Math check: response did not contain the expected FINAL OUTPUT "
            "block. Raw response saved to review/math_check_debug.txt for "
            "inspection."
        )

    fp["review_dir"].mkdir(parents=True, exist_ok=True)
    fp["math_check_output"].write_text(text, encoding="utf-8")
    _log("    Math check saved -> review/math_check_output.txt")
    return text


# ── Phase 2 review — step 2: full rubric review ────────────────────────────────
def run_rubric_review(fp: dict, client, prompts: dict, lesson_profile_text: str,
                       math_check_output: str, lesson: dict, questions: list,
                       images: Optional[dict] = None) -> str:
    """Calls review_rubric.md and saves the HTML output to
    review/review_report.html — the deliverable of Phase 2 review."""
    if images is None:
        images, _ = gather_item_images(fp, questions)

    template = prompts["rubric"]
    for ph in (PH_MATH_CHECK_OUTPUT, PH_LESSON_PROFILE, PH_EXIT_TICKET_ITEMS):
        if ph not in template:
            raise ValueError(f"Placeholder not found in review_rubric.md: '{ph}'")

    items_text = format_items_text(lesson, questions)
    prompt_text = (
        template.replace(PH_MATH_CHECK_OUTPUT, math_check_output)
                .replace(PH_LESSON_PROFILE, lesson_profile_text)
                .replace(PH_EXIT_TICKET_ITEMS, items_text)
    )
    content = _build_content_with_images(prompt_text, questions, images)

    raw = _stream(client, model=MODEL, max_tokens=32000,
                  messages=[{"role": "user", "content": content}])

    html = raw.strip()
    fence_m = re.match(r"^```(?:html)?\s*\n(.*?)\n```\s*$", html, re.DOTALL)
    if fence_m:
        html = fence_m.group(1).strip()

    if "<html" not in html.lower():
        fp["review_dir"].mkdir(parents=True, exist_ok=True)
        debug = fp["review_dir"] / "rubric_review_debug.txt"
        debug.write_text(raw, encoding="utf-8")
        raise ValueError(
            "Rubric review: response was not a valid HTML document. Raw "
            "response saved to review/rubric_review_debug.txt for inspection."
        )

    fp["review_dir"].mkdir(parents=True, exist_ok=True)
    fp["review_report"].write_text(html, encoding="utf-8")
    _log("    Rubric review saved -> review/review_report.html")
    return html
