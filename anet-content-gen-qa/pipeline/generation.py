"""
pipeline/generation.py
=======================
Phase 1 and Phase 2a-2d of the anet-exit-ticket-studio pipeline: the LLM
calls that turn a confirmed lesson identity + uploaded Kiddom Markdown into
an approved EXIT_TICKET XML block.

Adapted from the team's proven `ETGenerator/app.py` (`run_phase1`...
`run_phase2d`, `_stream`, `_log`, `_elapsed`, `_missing_packages`) with two
structural changes, both driven by this app's own I/O:

1. Input is uploaded Kiddom Teacher/Student Edition Markdown, not a lesson
   PDF pulled from Google Drive — so Phase 1 sends plain text, not a base64
   PDF document block, and there is no "Item Creation Guidelines" PDF to
   attach (the new prompt_1_extract.md is self-contained and doesn't
   reference it).
2. Lesson identity is detected deterministically by `pipeline.identity_detect`
   and confirmed by the user in the Streamlit UI *before* this module runs —
   Phase 1 substitutes those confirmed values into `{{LESSON_IDENTITY}}`
   rather than re-deriving them from a PDF.

This module is deliberately free of Streamlit imports — every function takes
plain data (paths, dicts, strings) and an already-constructed Anthropic
client, so it can be exercised outside the app (tests, a REPL) without a
running UI. All file I/O is explicit (read/write via the `fp` paths dict)
so a partially-completed lesson is resumable exactly like ETGenerator's
original pipeline: app.py decides which phases to (re)run based on which
files already exist.
"""

from __future__ import annotations

import datetime
import json
import re
import time
from pathlib import Path
from typing import Optional

# ── Model ─────────────────────────────────────────────────────────────────────
# Same model string ETGenerator used for every phase call. No reason found to
# change it for this app's phases.
MODEL = "claude-sonnet-4-6"

# ── Prompt files (relative to the app's prompts/ directory) ───────────────────
PROMPT_FILES = {
    "p1":  "prompt_1_extract.md",
    "p2a": "prompt_2a_define.md",
    "p2b": "prompt_2b_create.md",
    "p2c": "prompt_2c_review.md",
    "p2d": "prompt_2d_bias.md",
}

# Placeholder tokens, verified against each prompt's "## Inputs provided to
# you" section.
PH_LESSON_IDENTITY = "{{LESSON_IDENTITY}}"
PH_LESSON_MARKDOWN = "{{LESSON_MARKDOWN}}"
PH_LESSON_PROFILE  = "{{LESSON_PROFILE}}"
PH_ITEM_PLAN       = "{{ITEM_PLAN}}"
PH_RAW_EXIT_TICKET = "{{RAW_EXIT_TICKET}}"
PH_CONTENT_REVIEWED_EXIT_TICKET = "{{CONTENT_REVIEWED_EXIT_TICKET}}"

PHASES = ["p1", "p2a", "p2b", "p2c", "p2d", "p3"]


# ── Timestamp / logging helpers (reused verbatim from ETGenerator) ────────────
def _log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _elapsed(start: float) -> str:
    secs = int(time.time() - start)
    return f"{secs // 60}m {secs % 60}s" if secs >= 60 else f"{secs}s"


def _missing_packages() -> list:
    missing = []
    for pkg in ["anthropic"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


# ── API helper (reused verbatim from ETGenerator) ──────────────────────────────
def _stream(client, **kwargs) -> str:
    with client.messages.stream(**kwargs) as s:
        return s.get_final_text()


# ── Slug + path helpers ────────────────────────────────────────────────────────
_STATE_ABBR = {
    "virginia": "va",
    "maryland": "md",
    "georgia": "ga",
    "national": "national",
    "im 360": "im360",
    "im360": "im360",
    "im": "im",
}


def _clean_token(s: Optional[str]) -> str:
    s = (s or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def slugify(identity: dict) -> str:
    """
    Build a filesystem-safe slug from user-confirmed identity fields, e.g.
    {"curriculum_version": "Virginia", "grade": "3", "unit": "8",
     "lesson_number": "15"} -> "va-grade3-unit8-lesson15".

    Never raises — missing fields are simply omitted from the slug, and an
    all-blank identity falls back to "lesson" (still unique enough combined
    with a timestamp suffix the caller can add if a collision matters).
    """
    version = (identity.get("curriculum_version") or "").strip().lower()
    version_slug = _STATE_ABBR.get(version) or _clean_token(version)
    grade = _clean_token(identity.get("grade"))
    unit = _clean_token(identity.get("unit"))
    lesson_number = _clean_token(identity.get("lesson_number"))

    parts = [version_slug] if version_slug else []
    if grade:
        parts.append(f"grade{grade}")
    if unit:
        parts.append(f"unit{unit}")
    if lesson_number:
        parts.append(f"lesson{lesson_number}")
    return "-".join(parts) or "lesson"


def get_lesson_paths(output_root: Path, slug: str) -> dict:
    """All relevant paths for one lesson, mirroring ETGenerator's
    `get_lesson_paths` / resumability pattern but rooted at output/<slug>/
    instead of next to a Drive PDF."""
    output_dir   = Path(output_root) / slug
    inter_dir    = output_dir / "intermediate"
    visuals_dir  = output_dir / "visuals"
    review_dir   = output_dir / "review"
    return {
        "slug":                 slug,
        "output_dir":           output_dir,
        "intermediate_dir":     inter_dir,
        "visuals_dir":          visuals_dir,
        "review_dir":           review_dir,
        "uploaded_te":          output_dir / "uploaded_te.md",
        "uploaded_se":          output_dir / "uploaded_se.md",
        "identity_json":        output_dir / "identity.json",
        "approved_json":        output_dir / "approved.json",
        "lesson_profile":       inter_dir / "lesson_profile.txt",
        "item_plan":            inter_dir / "item_plan.xml",
        "exit_ticket_raw":      inter_dir / "exit_ticket_raw.xml",
        "exit_ticket_reviewed": inter_dir / "exit_ticket_reviewed.xml",
        "exit_ticket_final":    inter_dir / "exit_ticket.xml",
        "html_file":            output_dir / "exit_ticket.html",
        "math_check_output":    review_dir / "math_check_output.txt",
        "review_report":        review_dir / "review_report.html",
    }


def ensure_lesson_dirs(fp: dict) -> None:
    fp["output_dir"].mkdir(parents=True, exist_ok=True)
    fp["intermediate_dir"].mkdir(parents=True, exist_ok=True)
    fp["visuals_dir"].mkdir(parents=True, exist_ok=True)


def get_lesson_status(fp: dict) -> dict:
    """Returns {'state': 'complete'|'partial'|'new', 'done': [...]},
    mirroring ETGenerator's get_lesson_status but keyed off this app's
    per-lesson folder instead of a Drive-relative html filename."""
    if fp["html_file"].exists():
        return {"state": "complete", "done": list(PHASES)}
    if not fp["output_dir"].exists():
        return {"state": "new", "done": []}
    done = []
    if fp["lesson_profile"].exists():       done.append("p1")
    if fp["item_plan"].exists():            done.append("p2a")
    if fp["exit_ticket_raw"].exists():      done.append("p2b")
    if fp["exit_ticket_reviewed"].exists(): done.append("p2c")
    if fp["exit_ticket_final"].exists():    done.append("p2d")
    return {"state": "partial" if done else "new", "done": done}


def is_approved(fp: dict) -> bool:
    return fp["approved_json"].exists()


def mark_approved(fp: dict) -> None:
    fp["approved_json"].write_text(
        json.dumps({"approved_at": datetime.datetime.now().isoformat()}, indent=2),
        encoding="utf-8",
    )


# ── Prompt loading ──────────────────────────────────────────────────────────────
def load_prompts(prompts_dir: Path) -> dict:
    """Read each phase prompt file whole. Unlike ETGenerator's older prompts,
    these files have no separate '## The Prompt' section to extract — the
    entire file (framing, rules, and the {{PLACEHOLDER}} input block) is the
    literal prompt text sent to Claude."""
    prompts_dir = Path(prompts_dir)
    out = {}
    for key, filename in PROMPT_FILES.items():
        path = prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        out[key] = path.read_text(encoding="utf-8")
    return out


# ── Identity / lesson-markdown text builders ────────────────────────────────────
def build_identity_text(identity: dict) -> str:
    """Plain-text {{LESSON_IDENTITY}} block built from the *user-confirmed*
    identity fields (not the raw DetectedIdentity), since the user may have
    corrected them in the confirmation form."""
    standards = identity.get("standards") or []
    if isinstance(standards, str):
        standards = [s.strip() for s in standards.split(",") if s.strip()]

    lesson_number = (identity.get("lesson_number") or "").strip()
    lesson_title  = (identity.get("lesson_title") or "").strip()
    lesson_line = (
        f"Lesson {lesson_number}: {lesson_title}" if lesson_number or lesson_title
        else "Lesson: (not provided)"
    )

    return (
        f"{lesson_line}\n"
        f"Curriculum version: {identity.get('curriculum_version') or ''}\n"
        f"Grade: {identity.get('grade') or ''}\n"
        f"Unit: {identity.get('unit') or ''}\n"
        f"Standards addressed: {', '.join(standards)}"
    )


def build_lesson_markdown(te_text: str, se_text: Optional[str] = None) -> str:
    """Concatenate the uploaded Teacher Edition (required) and Student
    Edition (optional) markdown into the {{LESSON_MARKDOWN}} block, clearly
    labeled/separated when both are present, TE only otherwise."""
    te_text = (te_text or "").strip()
    if se_text and se_text.strip():
        return (
            "=== TEACHER EDITION (Kiddom export) ===\n\n"
            f"{te_text}\n\n"
            "=== STUDENT EDITION (Kiddom export) ===\n\n"
            f"{se_text.strip()}"
        )
    return f"=== TEACHER EDITION (Kiddom export) ===\n\n{te_text}"


# ── Phase functions ─────────────────────────────────────────────────────────────
# Each phase follows ETGenerator's hardened pattern exactly: build a prompt
# from the previous phase's saved output, call _stream, regex out the
# expected tagged block (with a code-fence fallback for when Claude wraps
# its output), and on total failure save the raw response to a *_debug.txt
# file and raise a clear ValueError the UI can surface.

def run_phase1(fp: dict, client, prompts: dict) -> str:
    """Extract the structured lesson profile from the uploaded Kiddom
    markdown + the user-confirmed identity. Unlike Phases 2a-2d, the new
    prompt_1_extract.md's output has no closing tag (it's a free-form
    Markdown section, not machine-parsed XML), so the "tagged block" this
    phase looks for is the '### STRUCTURED LESSON PROFILE' header rather
    than an <TAG>...</TAG> pair — the debug-on-failure behavior is the same."""
    identity = json.loads(fp["identity_json"].read_text(encoding="utf-8"))
    identity_text = build_identity_text(identity)

    te_text = fp["uploaded_te"].read_text(encoding="utf-8") if fp["uploaded_te"].exists() else ""
    se_text = fp["uploaded_se"].read_text(encoding="utf-8") if fp["uploaded_se"].exists() else None
    lesson_markdown = build_lesson_markdown(te_text, se_text)

    template = prompts["p1"]
    if PH_LESSON_IDENTITY not in template or PH_LESSON_MARKDOWN not in template:
        raise ValueError(
            f"Placeholder(s) not found in prompt_1_extract.md "
            f"('{PH_LESSON_IDENTITY}' / '{PH_LESSON_MARKDOWN}')"
        )
    prompt = template.replace(PH_LESSON_IDENTITY, identity_text).replace(
        PH_LESSON_MARKDOWN, lesson_markdown
    )

    raw = _stream(client, model=MODEL, max_tokens=32000,
                  messages=[{"role": "user", "content": prompt}])

    text = raw.strip()
    fence_m = re.match(r"^```(?:\w+)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    if fence_m:
        text = fence_m.group(1).strip()

    if "STRUCTURED LESSON PROFILE" not in text:
        debug = fp["intermediate_dir"] / "phase1_debug.txt"
        debug.write_text(raw, encoding="utf-8")
        raise ValueError(
            "Phase 1: response did not contain a STRUCTURED LESSON PROFILE "
            "section. Raw response saved to intermediate/phase1_debug.txt "
            "for inspection."
        )
    fp["lesson_profile"].write_text(text, encoding="utf-8")
    return text


def run_phase2a(fp: dict, client, prompts: dict) -> str:
    """Define item plan from lesson profile."""
    profile  = fp["lesson_profile"].read_text(encoding="utf-8")
    template = prompts["p2a"]
    if PH_LESSON_PROFILE not in template:
        raise ValueError(f"Placeholder not found in prompt_2a_define.md: '{PH_LESSON_PROFILE}'")
    prompt = template.replace(PH_LESSON_PROFILE, profile)

    raw = _stream(client, model=MODEL, max_tokens=16000,
                  messages=[{"role": "user", "content": prompt}])

    m = re.search(r"<ITEM_PLAN[^>]*>.*?</ITEM_PLAN>", raw, re.DOTALL | re.IGNORECASE)
    if not m:
        fence = re.search(r"```[\s\S]*?(<ITEM_PLAN[^>]*>[\s\S]*?</ITEM_PLAN>)", raw, re.IGNORECASE)
        if fence:
            m = fence
    if not m:
        debug = fp["intermediate_dir"] / "phase2a_debug.txt"
        debug.write_text(raw, encoding="utf-8")
        raise ValueError(
            "Phase 2a: no <ITEM_PLAN> block in response. Raw response saved "
            "to intermediate/phase2a_debug.txt for inspection."
        )
    item_plan = m.group(1) if (m.lastindex and m.lastindex >= 1) else m.group(0)
    fp["item_plan"].write_text(item_plan, encoding="utf-8")
    return item_plan


def run_phase2b(fp: dict, client, prompts: dict) -> str:
    """Create raw exit ticket XML from item plan."""
    item_plan = fp["item_plan"].read_text(encoding="utf-8")
    template  = prompts["p2b"]
    if PH_ITEM_PLAN not in template:
        raise ValueError(f"Placeholder not found in prompt_2b_create.md: '{PH_ITEM_PLAN}'")
    prompt = template.replace(PH_ITEM_PLAN, item_plan)

    raw = _stream(client, model=MODEL, max_tokens=32000,
                  messages=[{"role": "user", "content": prompt}])

    m = re.search(r"<EXIT_TICKET[^>]*>.*?</EXIT_TICKET>", raw, re.DOTALL | re.IGNORECASE)
    if not m:
        fence_m = re.search(r"```(?:xml)?[\s\S]*?(<EXIT_TICKET[^>]*>[\s\S]*?</EXIT_TICKET>)", raw, re.IGNORECASE)
        if fence_m:
            m = fence_m
    if not m:
        debug = fp["intermediate_dir"] / "phase2b_debug.txt"
        debug.write_text(raw, encoding="utf-8")
        raise ValueError("Phase 2b: no <EXIT_TICKET> block. Raw saved to intermediate/phase2b_debug.txt")
    raw_xml = m.group(0) if not (m.lastindex and m.lastindex >= 1) else m.group(1)
    fp["exit_ticket_raw"].write_text(raw_xml, encoding="utf-8")
    return raw_xml


def run_phase2c(fp: dict, client, prompts: dict) -> str:
    """Content review of the raw exit ticket XML."""
    raw_xml  = fp["exit_ticket_raw"].read_text(encoding="utf-8")
    template = prompts["p2c"]
    if PH_RAW_EXIT_TICKET not in template:
        raise ValueError(f"Placeholder not found in prompt_2c_review.md: '{PH_RAW_EXIT_TICKET}'")
    prompt = template.replace(PH_RAW_EXIT_TICKET, raw_xml)

    raw = _stream(client, model=MODEL, max_tokens=32000,
                  messages=[{"role": "user", "content": prompt}])

    m = re.search(r"<EXIT_TICKET[^>]*>.*?</EXIT_TICKET>", raw, re.DOTALL | re.IGNORECASE)
    if not m:
        fence_m = re.search(r"```(?:xml)?[\s\S]*?(<EXIT_TICKET[^>]*>[\s\S]*?</EXIT_TICKET>)", raw, re.IGNORECASE)
        if fence_m:
            m = fence_m
    if not m:
        debug = fp["intermediate_dir"] / "phase2c_debug.txt"
        debug.write_text(raw, encoding="utf-8")
        raise ValueError("Phase 2c: no <EXIT_TICKET> block. Raw saved to intermediate/phase2c_debug.txt")
    reviewed_xml = m.group(0) if not (m.lastindex and m.lastindex >= 1) else m.group(1)
    fp["exit_ticket_reviewed"].write_text(reviewed_xml, encoding="utf-8")
    return reviewed_xml


def run_phase2d(fp: dict, client, prompts: dict) -> str:
    """Bias & language review — final generation-stage output, written to
    exit_ticket.xml. This is the file the in-app editor works against, and
    the file that becomes the approved content when the user signs off."""
    reviewed_xml = fp["exit_ticket_reviewed"].read_text(encoding="utf-8")
    template     = prompts["p2d"]
    if PH_CONTENT_REVIEWED_EXIT_TICKET not in template:
        raise ValueError(
            f"Placeholder not found in prompt_2d_bias.md: '{PH_CONTENT_REVIEWED_EXIT_TICKET}'"
        )
    prompt = template.replace(PH_CONTENT_REVIEWED_EXIT_TICKET, reviewed_xml)

    raw = _stream(client, model=MODEL, max_tokens=32000,
                  messages=[{"role": "user", "content": prompt}])

    m = re.search(r"<EXIT_TICKET[^>]*>.*?</EXIT_TICKET>", raw, re.DOTALL | re.IGNORECASE)
    if not m:
        fence_m = re.search(r"```(?:xml)?[\s\S]*?(<EXIT_TICKET[^>]*>[\s\S]*?</EXIT_TICKET>)", raw, re.IGNORECASE)
        if fence_m:
            m = fence_m
    if not m:
        debug = fp["intermediate_dir"] / "phase2d_debug.txt"
        debug.write_text(raw, encoding="utf-8")
        raise ValueError("Phase 2d: no <EXIT_TICKET> block. Raw saved to intermediate/phase2d_debug.txt")
    final_xml = m.group(0) if not (m.lastindex and m.lastindex >= 1) else m.group(1)
    fp["exit_ticket_final"].write_text(final_xml, encoding="utf-8")
    return final_xml
