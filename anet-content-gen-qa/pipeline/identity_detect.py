"""
identity_detect.py
===================
Auto-detects lesson identity (curriculum version, state, grade, unit, lesson
number/title, and standard codes) from an uploaded Kiddom lesson Markdown
export, so the user can confirm/correct it in one glance instead of typing it
in by hand.

This is deliberately plain-Python regex, not an LLM call. The Kiddom export
format is structured and consistent (confirmed against a real production
export — see `item-generator/lessons/va-grade3-unit8-lesson15/` on the
reference Desktop and `item-generator/style/lesson-input-schema.md`'s "What a
real Kiddom lesson export contains" section):

    # Lesson 15: Equal or Not Equal?
    Kiddom Virginia Math, Grade 3, Unit 8 (Teacher Edition, as exported from Kiddom)

    ## Addressing standards
    3.CE.1.d

A deterministic parse of that header is faster, free, and more reliable than
asking an LLM to do it — and importantly, it's easy for a human to audit when
it gets something wrong. Detection is confidence-scored and every field
degrades to `None` (never a guess) when the pattern doesn't match, so the
Streamlit UI can show a blank for the user to fill in rather than silently
propagating a wrong value.

This module answers "what does the document say about itself." It never
overrides what the user confirms — the app always uses the user-confirmed
values downstream, not these raw detections, once confirmation happens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Curriculum "flavor" Kiddom tags a lesson with. Matched case-insensitively;
# "National" and bare "IM 360" both map to curriculum_version="National" /
# "IM 360" respectively, since production planning (per lesson-input-schema.md)
# treats state versions and National as differing only in standard-code tag,
# not underlying content. New states can be added here as ANet's production
# scope grows — an unmatched name still gets captured via the generic pattern
# below, just without a normalized/known flag.
KNOWN_STATES = {
    "virginia": "Virginia",
    "maryland": "Maryland",
    "georgia": "Georgia",
}


@dataclass
class DetectedIdentity:
    lesson_number: str | None = None
    lesson_title: str | None = None
    curriculum_version: str | None = None   # e.g. "Virginia", "National", "IM 360"
    grade: str | None = None                # e.g. "3", "K"
    unit: str | None = None                 # e.g. "8"
    edition_type: str | None = None         # "Teacher Edition" / "Student Edition" / None
    standards: list[str] = field(default_factory=list)   # e.g. ["3.CE.1.d"]
    warnings: list[str] = field(default_factory=list)
    confidence: str = "none"                # "high" | "partial" | "none"

    @property
    def is_known_state(self) -> bool:
        return (self.curriculum_version or "") in KNOWN_STATES.values()

    def as_display_dict(self) -> dict:
        """Flat dict for a Streamlit confirmation form."""
        return {
            "Lesson": f"Lesson {self.lesson_number}: {self.lesson_title}"
                      if self.lesson_number and self.lesson_title else (self.lesson_title or ""),
            "Curriculum version": self.curriculum_version or "",
            "Grade": self.grade or "",
            "Unit": self.unit or "",
            "Standards addressed": ", ".join(self.standards) if self.standards else "",
        }


_TITLE_RE = re.compile(
    r"^#\s*Lesson\s+([A-Za-z0-9]+)\s*:\s*(.+?)\s*$", re.MULTILINE
)
# "Kiddom Virginia Math, Grade 3, Unit 8 (Teacher Edition, as exported from Kiddom)"
# Grade is captured loosely (\S+) to allow "K" / "K.5" / "3" etc.
_SUBTITLE_RE = re.compile(
    r"^Kiddom\s+(?P<version>.+?)\s+Math\s*,\s*Grade\s+(?P<grade>\S+)\s*,\s*Unit\s+(?P<unit>\S+?)"
    r"(?:\s*\((?P<edition>[^)]*)\))?\s*$",
    re.MULTILINE,
)
_STANDARDS_SECTION_RE = re.compile(
    r"^##\s*Addressing standards?\s*\n(.+?)(?:\n##|\n---|\Z)",
    re.MULTILINE | re.DOTALL,
)
# Individual standard-code tokens on the "Addressing standards" line(s) —
# split on commas/whitespace, keep anything that looks like a code (has at
# least one digit and one separator character).
_STANDARD_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)+")


def detect_identity(markdown_text: str) -> DetectedIdentity:
    """
    Parse a Kiddom lesson export (Teacher Edition and/or Student Edition
    Markdown, whichever was uploaded — both carry the same header) and return
    a best-effort DetectedIdentity. Never raises; an unparseable document just
    comes back with confidence="none" and every field blank, which the
    Streamlit UI treats as "ask the user to fill this in by hand."
    """
    result = DetectedIdentity()
    text = markdown_text or ""

    title_m = _TITLE_RE.search(text)
    if title_m:
        result.lesson_number = title_m.group(1).strip()
        result.lesson_title = title_m.group(2).strip()

    subtitle_m = _SUBTITLE_RE.search(text)
    if subtitle_m:
        raw_version = subtitle_m.group("version").strip()
        result.grade = subtitle_m.group("grade").strip()
        result.unit = subtitle_m.group("unit").strip()
        result.edition_type = (subtitle_m.group("edition") or "").split(",")[0].strip() or None

        normalized = KNOWN_STATES.get(raw_version.lower())
        result.curriculum_version = normalized or raw_version
        if not normalized and raw_version.lower() not in ("national", "im 360", "im"):
            result.warnings.append(
                f"Curriculum version \"{raw_version}\" isn't one of the known tags "
                f"({', '.join(KNOWN_STATES.values())}, National, IM 360) — captured as-is, "
                f"please confirm it's right."
            )
    else:
        result.warnings.append(
            "Couldn't find the \"Kiddom <Version> Math, Grade X, Unit Y\" subtitle line — "
            "this may not be a standard Kiddom export, or its format has changed. "
            "Please fill in curriculum version / grade / unit manually."
        )

    standards_m = _STANDARDS_SECTION_RE.search(text)
    if standards_m:
        tokens = _STANDARD_TOKEN_RE.findall(standards_m.group(1))
        # De-dupe while preserving order.
        seen = set()
        for t in tokens:
            if t not in seen:
                seen.add(t)
                result.standards.append(t)
    if not result.standards:
        result.warnings.append(
            "No lesson-level standard code found under \"Addressing standards\" — "
            "check Steps 1/3 of the extraction output for standards found deeper in "
            "the document (a warm-up or cool-down can carry its own tag)."
        )

    if title_m and subtitle_m and result.standards:
        result.confidence = "high"
    elif title_m or subtitle_m:
        result.confidence = "partial"
    else:
        result.confidence = "none"

    return result
