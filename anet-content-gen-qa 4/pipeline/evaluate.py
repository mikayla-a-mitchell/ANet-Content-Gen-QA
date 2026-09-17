"""
Evaluation mode — review items authored somewhere else.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The creation side generates items and then reviews them. This side skips the
generating: a PDF of items authored in ACT (or anywhere else) plus the lesson
export go in, and the same review machinery runs on them.

The trick is that extraction lands the items in the app's own EXIT_TICKET
schema, so from that point on an evaluated set is indistinguishable from an
authored one. It gets the free mechanical checks, the findings queue, the
math check, the rubric review, the QA report and the archive — none of which
needed changing to support this.

What deliberately does NOT run here is Phase 2c/2d. Those rewrite items, and
these items belong to someone else: the job is to report on them, not to
quietly improve them.

    upload PDF + Kiddom export
      -> detect identity (identity_detect, unchanged)
      -> Phase 1 lesson profile from the export (generation.run_phase1, unchanged)
      -> extract items from the PDF into EXIT_TICKET XML   <- this module
      -> render (render.render_lesson, unchanged)
      -> review exactly as on the creation side

`evaluation.json` in the lesson folder marks the source, so the library can
tell the two streams apart and the QA report can say where the items came
from.
"""

from __future__ import annotations

import base64
import datetime
import json
import pathlib
import re

MODEL = "claude-sonnet-4-6"
EXTRACTION_PROMPT_FILE = "review_extraction.md"

PH_LESSON_IDENTITY = "{{LESSON_IDENTITY}}"

MAX_PDF_MB = 28  # the API's document limit is 32MB; leave headroom for the prompt


def load_extraction_prompt(prompts_dir: pathlib.Path) -> str:
    path = pathlib.Path(prompts_dir) / EXTRACTION_PROMPT_FILE
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def mark_evaluation(fp: dict, pdf_name: str, item_count: int | None = None) -> None:
    fp["output_dir"].mkdir(parents=True, exist_ok=True)
    (fp["output_dir"] / "evaluation.json").write_text(
        json.dumps({
            "source": "pdf",
            "pdf_name": pdf_name,
            "items": item_count,
            "extracted_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }, indent=2),
        encoding="utf-8",
    )


def is_evaluation(fp_or_dir) -> bool:
    d = fp_or_dir["output_dir"] if isinstance(fp_or_dir, dict) else pathlib.Path(fp_or_dir)
    return (pathlib.Path(d) / "evaluation.json").exists()


def evaluation_info(fp_or_dir) -> dict:
    d = fp_or_dir["output_dir"] if isinstance(fp_or_dir, dict) else pathlib.Path(fp_or_dir)
    p = pathlib.Path(d) / "evaluation.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _identity_text(identity: dict) -> str:
    standards = identity.get("standards") or []
    return (
        f"Lesson number: {identity.get('lesson_number', '') or ''}\n"
        f"Lesson title: {identity.get('lesson_title', '') or ''}\n"
        f"Curriculum version: {identity.get('curriculum_version', '') or ''}\n"
        f"Grade: {identity.get('grade', '') or ''}\n"
        f"Unit: {identity.get('unit', '') or ''}\n"
        f"Standards: {', '.join(standards)}\n"
    )


def _stream(client, **kwargs) -> str:
    """Same streaming call shape the generation and review modules use, so a
    long extraction can't hit a non-streaming timeout."""
    chunks = []
    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            chunks.append(text)
    return "".join(chunks)


def extract_items_from_pdf(fp: dict, client, prompt_template: str,
                           identity: dict, pdf_bytes: bytes,
                           pdf_name: str = "items.pdf") -> str:
    """Send the PDF to the model and write the extracted EXIT_TICKET XML to
    the lesson's final XML path. Returns the XML.

    The PDF goes as a document content block, so the model reads the real
    pages — layout, figures and all — rather than a lossy text dump. That is
    the same reason the original ItemReviewer worked from a rendered page
    image instead of extracted text."""
    size_mb = len(pdf_bytes) / (1024 * 1024)
    if size_mb > MAX_PDF_MB:
        raise ValueError(
            f"That PDF is {size_mb:.1f}MB, over the {MAX_PDF_MB}MB limit for a single "
            f"request. Split it and evaluate the parts separately."
        )
    if not pdf_bytes[:5].startswith(b"%PDF"):
        raise ValueError("That file does not look like a PDF (missing the %PDF header).")

    if PH_LESSON_IDENTITY not in prompt_template:
        raise ValueError(
            f"Placeholder not found in {EXTRACTION_PROMPT_FILE}: '{PH_LESSON_IDENTITY}'")
    prompt = prompt_template.replace(PH_LESSON_IDENTITY, _identity_text(identity))

    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.standard_b64encode(pdf_bytes).decode("ascii"),
            },
        },
        {"type": "text", "text": prompt},
    ]

    raw = _stream(client, model=MODEL, max_tokens=32000,
                  messages=[{"role": "user", "content": content}])

    m = re.search(r"<EXIT_TICKET[^>]*>.*?</EXIT_TICKET>", raw, re.DOTALL | re.IGNORECASE)
    if not m:
        fence = re.search(
            r"```(?:xml)?[\s\S]*?(<EXIT_TICKET[^>]*>[\s\S]*?</EXIT_TICKET>)", raw, re.IGNORECASE)
        m = fence
    if not m:
        fp["intermediate_dir"].mkdir(parents=True, exist_ok=True)
        (fp["intermediate_dir"] / "extraction_debug.txt").write_text(raw, encoding="utf-8")
        raise ValueError(
            "Extraction: no <EXIT_TICKET> block in the response. Raw output saved to "
            "intermediate/extraction_debug.txt"
        )
    xml = m.group(1) if (m.lastindex or 0) >= 1 else m.group(0)

    # Comparison symbols in extracted items are bare "<" in the model's
    # output, which is illegal XML text; normalise before anything parses it.
    from .validate import sanitize_item_xml
    xml = sanitize_item_xml(xml)

    fp["intermediate_dir"].mkdir(parents=True, exist_ok=True)
    # Keep the extraction as its own artifact as well as the working copy, so
    # "what did the PDF actually say" survives later edits.
    (fp["intermediate_dir"] / "extracted_items.xml").write_text(xml, encoding="utf-8")
    fp["exit_ticket_final"].write_text(xml, encoding="utf-8")
    return xml


def extraction_note(xml: str) -> str:
    """The extractor's own uncertainty list, for surfacing in the app."""
    m = re.search(r"<EXTRACTION_NOTE>(.*?)</EXTRACTION_NOTE>", xml, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    note = re.sub(r"\s+", " ", m.group(1)).strip()
    return "" if note.lower().rstrip(".") in ("none", "") else note
