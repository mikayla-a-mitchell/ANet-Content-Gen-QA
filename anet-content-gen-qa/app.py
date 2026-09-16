"""
ANet Exit Ticket Studio
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One workspace per lesson: author, get suggestions, fix, review, approve —
without ever leaving the screen or losing the ability to edit.

Library        — lessons filed by curriculum / grade / unit / lesson.
Items          — the editable item set. Editable at every status, always.
Suggestions    — findings queue. Local mechanical checks run free on every
                 save; the model review (math check + rubric) runs on demand.
                 Both land in one list with Accept / Reject / note per finding.
Preview        — the rendered student-facing exit ticket.
QA report      — the shareable review record, archived per run.

The old two-stage flow (approve, *then* review) has been inverted: review
runs while you author, and approving is the sign-off that the findings are
resolved. Approving no longer takes the editor away; editing an approved
lesson clears the approval instead, so the sign-off can never be stale.

Generation and the model review need ANTHROPIC_API_KEY. Everything else —
editing, local validation, rendering, the report viewer — works without it.

Pipeline logic lives in pipeline/generation.py (Phases 1, 2a-2d),
pipeline/render.py (Phase 3 — parsing + HTML, no API), pipeline/review.py
(Phase 2 review) and pipeline/validate.py (local checks, no API). This file
owns every Streamlit call and all session state.
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import time

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

APP_DIR = pathlib.Path(__file__).parent
load_dotenv(APP_DIR / ".env")

from pipeline import generation as gen  # noqa: E402
from pipeline import identity_detect  # noqa: E402
from pipeline import evaluate as eval_mod  # noqa: E402
from pipeline import profiles as profiles_mod  # noqa: E402
from pipeline import render as render_mod  # noqa: E402
from pipeline import review as review_mod  # noqa: E402
from pipeline import validate as validate_mod  # noqa: E402
import png_export  # noqa: E402

st.set_page_config(page_title="ANet Exit Ticket Studio", page_icon="📝", layout="wide")

PROMPTS_DIR    = APP_DIR / "prompts"
OUTPUT_DIR     = APP_DIR / "output"
RENDERERS_FILE = APP_DIR / "visual_renderers.py"

NEW_LESSON = "__new__"
ADD_PROFILE = "__add_profile__"
VIEWS = ["Items", "Suggestions", "Preview", "QA report"]

MODE_CREATE = "Create items"
MODE_EVAL = "Evaluate items"
MODES = [MODE_CREATE, MODE_EVAL]

STAGE_ACTIVE = "In progress"
STAGE_DONE = "Finished"

SEV_ICON = {"high": "🔴", "medium": "🟠", "low": "🟡"}
SEV_WORD = {"high": "Must fix", "medium": "Should fix", "low": "Style"}


# ── startup ───────────────────────────────────────────────────────────────────
def has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _run_startup_checks() -> None:
    missing = gen._missing_packages()
    if missing:
        st.error(f"Missing packages: **{', '.join(missing)}**  \nInstall them and restart.")
        st.stop()
    if not RENDERERS_FILE.exists():
        st.error("`visual_renderers.py` not found in the app folder.")
        st.stop()
    required = list(gen.PROMPT_FILES.values()) + list(review_mod.REVIEW_PROMPT_FILES.values())
    absent = [n for n in required if not (PROMPTS_DIR / n).exists()]
    if absent:
        st.error(f"Missing prompt file(s): `{'`, `'.join(absent)}` in `prompts/`.")
        st.stop()
    # No API key is not fatal: authoring, validation, rendering and the report
    # viewer all work offline. Only generation and the model review need it.
    if not has_api_key():
        st.sidebar.warning(
            "No `ANTHROPIC_API_KEY` in `.env`. You can edit, validate and view "
            "lessons; generating and running the model review are disabled."
        )


# ── whose workspace ───────────────────────────────────────────────────────────
def active_profile() -> dict | None:
    return st.session_state.get("profile")


def workspace() -> pathlib.Path:
    """Lessons live under the active person's folder. Every path in the app
    resolves through here, so there is one place that decides whose work is
    being shown."""
    p = active_profile()
    if p is None:
        return OUTPUT_DIR
    return profiles_mod.workspace_dir(OUTPUT_DIR, p)


def current_mode() -> str:
    return st.session_state.get("mode", MODE_CREATE)


def render_mode_toggle() -> str:
    """Create items (author here, then review) vs Evaluate items (review a
    PDF authored elsewhere). The toggle decides what new work starts and
    which stream the library shows; a lesson's own workspace looks the same
    either way, because after extraction an evaluated set is just a lesson."""
    st.sidebar.markdown("### Mode")
    mode = st.sidebar.radio(
        "mode", MODES, key="mode", label_visibility="collapsed",
        captions=["Author a new exit ticket, then review it",
                  "Upload a PDF of existing items and review those"],
    )
    return mode


def render_profile_picker() -> dict | None:
    roster = profiles_mod.load_profiles(OUTPUT_DIR)
    st.sidebar.markdown("### Workspace")

    # A freshly created profile is staged here so the selectbox below can be
    # pointed at it before the widget is drawn.
    pending = st.session_state.pop("_pending_profile", None)
    if pending:
        st.session_state["profile_select"] = pending

    options = [x["slug"] for x in roster] + [ADD_PROFILE]
    labels = {x["slug"]: x["name"] for x in roster}
    labels[ADD_PROFILE] = "＋ Add profile…"

    if st.session_state.get("profile_select") not in options:
        st.session_state["profile_select"] = roster[0]["slug"] if roster else ADD_PROFILE

    chosen = st.sidebar.selectbox(
        "Your name", options,
        format_func=lambda o: labels.get(o, o),
        key="profile_select",
        label_visibility="collapsed" if roster else "visible",
    )

    if chosen == ADD_PROFILE:
        with st.sidebar.form("add_profile_form", clear_on_submit=False):
            typed = st.text_input("Your name", placeholder="e.g. Mikayla")
            if st.form_submit_button("Add profile", type="primary"):
                profile, err = profiles_mod.add_profile(OUTPUT_DIR, typed)
                if err:
                    st.sidebar.error(err)
                else:
                    st.session_state["_pending_profile"] = profile["slug"]
                    st.session_state["_new_profile_name"] = profile["name"]
                    st.rerun()
        st.session_state["profile"] = None
        return None

    profile = next((x for x in roster if x["slug"] == chosen), None)
    st.session_state["profile"] = profile
    if profile:
        ws = profiles_mod.workspace_dir(OUTPUT_DIR, profile)
        ws.mkdir(parents=True, exist_ok=True)
        st.sidebar.caption(f"Working as **{profile['name']}**")

        # Lessons made before workspaces existed sit at the top of output/.
        # Offer them to whoever is here rather than silently hiding them.
        orphans = profiles_mod.legacy_lesson_dirs(OUTPUT_DIR)
        if orphans:
            st.sidebar.info(f"{len(orphans)} lesson(s) aren't in anyone's workspace yet.")
            if st.sidebar.button(f"Move them into {profile['name']}'s workspace",
                                 use_container_width=True):
                moved = profiles_mod.adopt_legacy_lessons(OUTPUT_DIR, profile)
                st.session_state["_adopted"] = moved
                st.rerun()
    return profile


# ── per-lesson paths not in generation.get_lesson_paths ───────────────────────
def extra_paths(fp: dict) -> dict:
    return {
        "decisions":      fp["review_dir"] / "decisions.json",
        "report_history": fp["review_dir"] / "history",
    }


def load_decisions(fp: dict) -> dict:
    p = extra_paths(fp)["decisions"]
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_decision(fp: dict, finding_id: str, action: str, note: str = "") -> None:
    p = extra_paths(fp)["decisions"]
    p.parent.mkdir(parents=True, exist_ok=True)
    data = load_decisions(fp)
    data[finding_id] = {
        "action": action,
        "note": note.strip(),
        "at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── library ───────────────────────────────────────────────────────────────────
def _read_identity(d: pathlib.Path) -> dict | None:
    f = d / "identity.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def lesson_index() -> list:
    """Every saved lesson in the active workspace, newest first."""
    root = workspace()
    if not root.exists():
        return []
    rows = []
    for d in root.iterdir():
        if not d.is_dir():
            continue
        ident = _read_identity(d)
        if ident is None:
            continue
        fp = gen.get_lesson_paths(root, d.name)
        rows.append({
            "slug": d.name,
            "identity": ident,
            "curriculum": (ident.get("curriculum_version") or "Unfiled").strip() or "Unfiled",
            "grade": (ident.get("grade") or "?").strip() or "?",
            "unit": (ident.get("unit") or "?").strip() or "?",
            "lesson_number": (ident.get("lesson_number") or "").strip(),
            "lesson_title": (ident.get("lesson_title") or d.name).strip(),
            "rendered": fp["html_file"].exists(),
            "reviewed": fp["review_report"].exists(),
            "approved": gen.is_approved(fp),
            "is_eval": eval_mod.is_evaluation(fp),
            "mtime": d.stat().st_mtime,
        })
    return sorted(rows, key=lambda r: r["mtime"], reverse=True)


def status_of(row: dict) -> str:
    if row["approved"]:
        return "Approved"
    if row["reviewed"]:
        return "Reviewed"
    if row["rendered"]:
        return "Draft"
    return "Not generated"


STATUS_ICON = {"Approved": "✅", "Reviewed": "🔎", "Draft": "✏️", "Not generated": "⬜"}


def _grade_key(g: str):
    return (0, int(g)) if g.isdigit() else (1, g)


def _sticky_select(label, options, key, format_func=None, container=None):
    """A selectbox whose remembered value is repaired before the widget is
    drawn. Without this, changing a filter (mode or stage) can leave a stale
    slug in session_state that is no longer among the options, which either
    throws or silently snaps to the wrong row."""
    container = container or st.sidebar
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    return container.selectbox(label, options, key=key,
                               format_func=format_func or (lambda x: x))


def _start_new() -> None:
    st.session_state["show_new"] = True


def _stop_new() -> None:
    """Choosing a lesson from the picker leaves the new-lesson screen."""
    st.session_state["show_new"] = False


def render_library() -> str:
    """Mode → stage → curriculum → grade → unit → lesson. Returns a slug, or
    NEW_LESSON when the new-lesson screen should be shown.

    The new-lesson request has to persist across the rerun: an earlier version
    set the return value directly and then fell through to the pickers below,
    which overwrote it every time, so the button never did anything."""
    want_eval = current_mode() == MODE_EVAL
    stream = [r for r in lesson_index() if r["is_eval"] == want_eval]

    st.sidebar.markdown("### Library")

    pending_stage = st.session_state.pop("_pending_stage", None)
    if pending_stage:
        st.session_state["lib_stage"] = pending_stage

    n_active = sum(1 for r in stream if not r["approved"])
    n_done = sum(1 for r in stream if r["approved"])
    stage = _sticky_select(
        "Stage", [STAGE_ACTIVE, STAGE_DONE], "lib_stage",
        format_func=lambda x: (f"{STAGE_ACTIVE} ({n_active})" if x == STAGE_ACTIVE
                               else f"{STAGE_DONE} ({n_done})"),
    )

    new_label = "＋  New evaluation" if want_eval else "＋  New lesson"
    st.sidebar.button(new_label, use_container_width=True, on_click=_start_new)

    rows = [r for r in stream if (r["approved"] if stage == STAGE_DONE else not r["approved"])]

    # A freshly created lesson stages its slug so the pickers below can be
    # pointed at it before they are instantiated.
    pending = st.session_state.pop("_pending_slug", None)
    if pending:
        p = next((r for r in rows if r["slug"] == pending), None)
        if p:
            st.session_state["show_new"] = False
            st.session_state["lib_curriculum"] = p["curriculum"]
            st.session_state["lib_grade"] = p["grade"]
            st.session_state["lib_unit"] = p["unit"]
            st.session_state["lib_lesson"] = p["slug"]

    if not rows:
        if stage == STAGE_DONE:
            st.sidebar.caption("Nothing approved yet.")
        else:
            st.sidebar.caption("Nothing in progress.")
        st.session_state["show_new"] = True
        return NEW_LESSON

    if st.session_state.get("show_new"):
        st.sidebar.caption("Starting something new — pick a lesson below to go back to it.")

    curricula = sorted({r["curriculum"] for r in rows})
    cur = _sticky_select("Curriculum", curricula, "lib_curriculum")

    grades = sorted({r["grade"] for r in rows if r["curriculum"] == cur}, key=_grade_key)
    grade = _sticky_select("Grade", grades, "lib_grade", lambda g: f"Grade {g}")

    units = sorted({r["unit"] for r in rows
                    if r["curriculum"] == cur and r["grade"] == grade}, key=_grade_key)
    unit = _sticky_select("Unit", units, "lib_unit", lambda u: f"Unit {u}")

    in_unit = [r for r in rows
               if r["curriculum"] == cur and r["grade"] == grade and r["unit"] == unit]
    in_unit.sort(key=lambda r: (_grade_key(r["lesson_number"] or "?"), r["lesson_title"]))
    labels = {
        r["slug"]: f"{STATUS_ICON[status_of(r)]} Lesson {r['lesson_number']}: {r['lesson_title']}"
                   .replace("Lesson : ", "")
        for r in in_unit
    }
    slugs = [r["slug"] for r in in_unit]
    if st.session_state.get("lib_lesson") not in slugs:
        st.session_state["lib_lesson"] = slugs[0]
    chosen = st.sidebar.selectbox(
        "Lesson", slugs, key="lib_lesson",
        format_func=lambda x: labels.get(x, x),
        on_change=_stop_new,
    )

    st.sidebar.caption(f"{len(stream)} in this stream · {n_done} approved")

    if st.session_state.get("show_new"):
        return NEW_LESSON
    return chosen


# ── new lesson ────────────────────────────────────────────────────────────────
def render_new_lesson() -> None:
    st.subheader("New lesson")
    st.caption("Upload the Kiddom export. The lesson's identity is read from the document header.")

    ugen = st.session_state.setdefault("upload_gen", 0)
    te_file = st.file_uploader("Teacher Edition markdown (required)",
                               type=["md", "markdown", "txt"], key=f"te_{ugen}")
    se_file = st.file_uploader("Student Edition markdown (optional)",
                               type=["md", "markdown", "txt"], key=f"se_{ugen}")
    if not te_file:
        st.info("Upload a Teacher Edition export to continue.")
        return

    te_text = te_file.getvalue().decode("utf-8", errors="replace")
    se_text = se_file.getvalue().decode("utf-8", errors="replace") if se_file else None

    detected = identity_detect.detect_identity(te_text)
    for w in detected.warnings:
        st.warning(w)
    if detected.confidence == "high":
        st.success("Identity detected from the document header — check it and confirm.")

    with st.form("identity_form"):
        c1, c2, c3 = st.columns(3)
        lesson_number = c1.text_input("Lesson number", value=detected.lesson_number or "")
        grade = c2.text_input("Grade", value=detected.grade or "")
        unit = c3.text_input("Unit", value=detected.unit or "")
        lesson_title = st.text_input("Lesson title", value=detected.lesson_title or "")
        curriculum_version = st.text_input("Curriculum version (state)",
                                           value=detected.curriculum_version or "")
        standards_str = st.text_input("Standards (comma-separated)",
                                      value=", ".join(detected.standards))
        if st.form_submit_button("Confirm identity", type="primary"):
            identity = {
                "lesson_number": lesson_number.strip(),
                "lesson_title": lesson_title.strip(),
                "curriculum_version": curriculum_version.strip(),
                "grade": grade.strip(),
                "unit": unit.strip(),
                "standards": [s.strip() for s in standards_str.split(",") if s.strip()],
            }
            slug = gen.slugify(identity)
            fp = gen.get_lesson_paths(workspace(), slug)
            gen.ensure_lesson_dirs(fp)
            fp["uploaded_te"].write_text(te_text, encoding="utf-8")
            if se_text:
                fp["uploaded_se"].write_text(se_text, encoding="utf-8")
            fp["identity_json"].write_text(json.dumps(identity, indent=2), encoding="utf-8")
            st.session_state["upload_gen"] = ugen + 1
            st.session_state["_pending_slug"] = slug
            st.session_state["nav_slug"] = slug
            st.rerun()


def render_new_evaluation() -> None:
    """Upload someone else's items plus the lesson they were written for, and
    put them through the same review the authoring side gets."""
    st.subheader("New evaluation")
    st.caption(
        "Upload the PDF of items to review, plus the Kiddom export for the lesson they "
        "were written for. The lesson export is what the review checks the items against — "
        "alignment, scope, number ranges and vocabulary all come from it."
    )

    ugen = st.session_state.setdefault("eval_upload_gen", 0)
    pdf_file = st.file_uploader("PDF of items (required)", type=["pdf"], key=f"epdf_{ugen}")
    te_file = st.file_uploader("Teacher Edition markdown (required)",
                               type=["md", "markdown", "txt"], key=f"ete_{ugen}")
    se_file = st.file_uploader("Student Edition markdown (optional)",
                               type=["md", "markdown", "txt"], key=f"ese_{ugen}")

    if not pdf_file or not te_file:
        st.info("Both the items PDF and the Teacher Edition export are needed to start.")
        return
    if not has_api_key():
        st.error("Evaluating needs `ANTHROPIC_API_KEY` in `.env` — extraction and the "
                 "review passes are model calls.")
        return

    pdf_bytes = pdf_file.getvalue()
    te_text = te_file.getvalue().decode("utf-8", errors="replace")
    se_text = se_file.getvalue().decode("utf-8", errors="replace") if se_file else None
    st.caption(f"`{pdf_file.name}` · {len(pdf_bytes)/1024/1024:.1f}MB")

    detected = identity_detect.detect_identity(te_text)
    for w in detected.warnings:
        st.warning(w)

    with st.form("eval_identity_form"):
        c1, c2, c3 = st.columns(3)
        lesson_number = c1.text_input("Lesson number", value=detected.lesson_number or "")
        grade = c2.text_input("Grade", value=detected.grade or "")
        unit = c3.text_input("Unit", value=detected.unit or "")
        lesson_title = st.text_input("Lesson title", value=detected.lesson_title or "")
        curriculum_version = st.text_input("Curriculum version (state)",
                                           value=detected.curriculum_version or "")
        standards_str = st.text_input("Standards (comma-separated)",
                                      value=", ".join(detected.standards))
        go = st.form_submit_button("Extract items & prepare review", type="primary")

    if not go:
        return

    identity = {
        "lesson_number": lesson_number.strip(),
        "lesson_title": lesson_title.strip(),
        "curriculum_version": curriculum_version.strip(),
        "grade": grade.strip(),
        "unit": unit.strip(),
        "standards": [s.strip() for s in standards_str.split(",") if s.strip()],
    }
    slug = gen.slugify(identity)
    fp = gen.get_lesson_paths(workspace(), slug)
    if fp["output_dir"].exists() and not eval_mod.is_evaluation(fp):
        st.error(
            f"`{slug}` already exists in your workspace as an authored lesson. Rename the "
            f"lesson title slightly so the evaluation gets its own folder."
        )
        return
    gen.ensure_lesson_dirs(fp)
    fp["uploaded_te"].write_text(te_text, encoding="utf-8")
    if se_text:
        fp["uploaded_se"].write_text(se_text, encoding="utf-8")
    fp["identity_json"].write_text(json.dumps(identity, indent=2), encoding="utf-8")
    (fp["output_dir"] / "source_items.pdf").write_bytes(pdf_bytes)

    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    # The lesson profile is what the rubric review measures the items against,
    # so evaluation still runs Phase 1 — just not 2a-2d, which would author.
    if not fp["lesson_profile"].exists():
        with st.spinner("Reading the lesson (Phase 1)…"):
            try:
                gen.run_phase1(fp, client, gen.load_prompts(PROMPTS_DIR))
            except ValueError as e:
                st.error(f"Lesson extraction failed: {e}")
                return

    with st.spinner("Extracting items from the PDF…"):
        try:
            xml = eval_mod.extract_items_from_pdf(
                fp, client, eval_mod.load_extraction_prompt(PROMPTS_DIR),
                identity, pdf_bytes, pdf_file.name)
        except ValueError as e:
            st.error(f"Extraction failed: {e}")
            return

    try:
        _, qs = render_mod.parse_exit_ticket(xml)
    except ValueError as e:
        st.error(f"The extracted items were not valid XML: {e}")
        return

    eval_mod.mark_evaluation(fp, pdf_file.name, len(qs))
    with st.spinner("Rendering…"):
        render_mod.render_lesson(fp, xml_text=xml)

    st.session_state["eval_upload_gen"] = ugen + 1
    st.session_state["_pending_slug"] = slug
    st.session_state["nav_slug"] = slug
    st.session_state["_pending_view"] = "Suggestions"
    st.rerun()


# ── generation ────────────────────────────────────────────────────────────────
PHASE_LABELS = {"p1": "P1", "p2a": "2a", "p2b": "2b", "p2c": "2c", "p2d": "2d", "p3": "P3"}


def render_phase_row(ph, row: dict) -> None:
    with ph.container():
        cols = st.columns([1, 1, 1, 1, 1, 1, 5])
        for i, key in enumerate(gen.PHASES):
            cols[i].markdown(f"**{PHASE_LABELS[key]}**  \n{row.get(key, '⬜')}")
        msg = row.get("msg", "")
        color = "#c0392b" if "Error" in msg else ("#1a6e2e" if "done" in msg or "Complete" in msg else "inherit")
        cols[6].markdown(f"<span style='color:{color};font-size:13px'>{msg}</span>",
                         unsafe_allow_html=True)


PHASE_STEPS = [
    ("p1",  gen.run_phase1,  "Reading the lesson"),
    ("p2a", gen.run_phase2a, "Planning items"),
    ("p2b", gen.run_phase2b, "Writing items"),
    ("p2c", gen.run_phase2c, "Content review"),
    ("p2d", gen.run_phase2d, "Bias review"),
]
PHASE_FUNCS = {k: (f, lbl) for k, f, lbl in PHASE_STEPS}


def next_pending_phase(fp: dict) -> str | None:
    """The next phase with no output file yet, or None when the lesson is
    fully generated and rendered."""
    done = set(gen.get_lesson_status(fp)["done"])
    for key, _, _ in PHASE_STEPS:
        if key not in done:
            return key
    return None if fp["html_file"].exists() else "p3"


def run_one_phase(fp: dict, client, prompts: dict, key: str) -> dict | None:
    """Run exactly one phase. Returns None on success, or an error dict.

    One phase per script run, not the whole chain: a single phase can take
    minutes, and Streamlit abandons a script run if the browser's websocket
    reconnects while a callback is blocking. The old all-in-one loop lost its
    in-flight phase whenever that happened, which is why the Resume button
    kept coming back. Each phase writes its own output file, so advancing one
    at a time is both durable and visible."""
    t0 = time.time()
    try:
        if key == "p3":
            render_mod.render_lesson(fp)
        else:
            func, _ = PHASE_FUNCS[key]
            func(fp, client, prompts)
    except ValueError as e:
        return {"phase": key, "message": str(e)}
    except Exception as e:                      # renderer and transport errors
        return {"phase": key, "message": f"{type(e).__name__}: {e}"}
    st.session_state.setdefault("phase_times", {})[f"{fp['slug']}:{key}"] = time.time() - t0
    return None


# ── editing ───────────────────────────────────────────────────────────────────
def write_and_render(fp: dict, lesson: dict, questions: list) -> None:
    """Single path for every change — typed edits and accepted suggestions
    both come through here, so the XML and the HTML can never diverge."""
    xml = render_mod.build_exit_ticket_xml(lesson, questions)
    fp["exit_ticket_final"].write_text(xml, encoding="utf-8")
    render_mod.render_lesson(fp, xml_text=xml)
    # An approved lesson that changes is no longer the thing that was signed
    # off, so the approval is cleared rather than left to go stale.
    if gen.is_approved(fp):
        fp["approved_json"].rename(fp["approved_json"].with_suffix(".json.superseded"))
        st.session_state["_approval_cleared"] = True


def apply_patch(fp: dict, lesson: dict, questions: list, item: str,
                field: str, value: str) -> bool:
    """Write one field-level change. `field` is 'stem', 'prompt', 'correct',
    'choice.<L>' or 'rationale.<L>' — the shape validate.py emits."""
    q = next((x for x in questions if str(x["id"]) == str(item)), None)
    if q is None or field is None:
        return False
    if field in ("stem", "prompt", "correct"):
        q[field] = value
    elif field.startswith("choice."):
        lbl = field.split(".", 1)[1]
        target = next((c for c in q.get("choices", []) if c["label"] == lbl), None)
        if target is None:
            return False
        target["text"] = value
    elif field.startswith("rationale."):
        lbl = field.split(".", 1)[1]
        target = next((r for r in q.get("rationales", []) if r["label"] == lbl), None)
        if target is None:
            return False
        target["text"] = value
    else:
        return False
    write_and_render(fp, lesson, questions)
    return True


def render_items_view(fp: dict, slug: str, identity: dict) -> None:
    if not fp["html_file"].exists():
        if eval_mod.is_evaluation(fp):
            st.warning(
                "This evaluation has no rendered items — extraction did not finish. "
                "Start it again from ＋ New evaluation with the same PDF; the folder will "
                "be reused."
            )
        else:
            render_generate_panel(fp, slug)
        return

    lesson, questions = render_mod.parse_exit_ticket(
        fp["exit_ticket_final"].read_text(encoding="utf-8"))

    local = validate_mod.validate(lesson, questions)
    blocking = [f for f in local if f["severity"] == "high"]
    if blocking:
        st.warning(
            f"{len(blocking)} must-fix issue(s) found automatically — see the Suggestions tab."
        )

    st.caption("Edit any field and save. Saving re-renders the preview and re-runs the checks.")
    with st.form(f"edit_{slug}"):
        for q in questions:
            qid = q["id"]
            st.markdown(f"**Question {qid}**" +
                        (f" · `{q['standard']}`" if q.get("standard") else ""))
            c1, c2 = st.columns(2)
            c1.text_area("Stem (leave empty if none)", value=q.get("stem", ""),
                         key=f"{slug}_{qid}_stem", height=80)
            c2.text_area("Prompt", value=q.get("prompt", ""),
                         key=f"{slug}_{qid}_prompt", height=80)

            labels = [c["label"] for c in q.get("choices", [])] or ["A", "B", "C", "D"]
            cur = q.get("correct", "")
            st.radio("Correct answer", labels, horizontal=True,
                     index=labels.index(cur) if cur in labels else 0,
                     key=f"{slug}_{qid}_correct")

            for c in q.get("choices", []):
                cc1, cc2 = st.columns([1, 2])
                cc1.text_input(f"Choice {c['label']}", value=c.get("text", ""),
                               key=f"{slug}_{qid}_choice_{c['label']}")
                r = next((x for x in q.get("rationales", []) if x["label"] == c["label"]), None)
                cc2.text_input(f"Rationale {c['label']}",
                               value=(r or {}).get("text", ""),
                               key=f"{slug}_{qid}_rat_{c['label']}")
            st.divider()
        saved = st.form_submit_button("Save & re-render", type="primary")

    if saved:
        for q in questions:
            qid = q["id"]
            q["stem"] = st.session_state.get(f"{slug}_{qid}_stem", q.get("stem", ""))
            q["prompt"] = st.session_state.get(f"{slug}_{qid}_prompt", q.get("prompt", ""))
            q["correct"] = st.session_state.get(f"{slug}_{qid}_correct", q.get("correct", ""))
            for c in q.get("choices", []):
                c["text"] = st.session_state.get(
                    f"{slug}_{qid}_choice_{c['label']}", c.get("text", ""))
            for r in q.get("rationales", []):
                r["text"] = st.session_state.get(
                    f"{slug}_{qid}_rat_{r['label']}", r.get("text", ""))
        with st.spinner("Saving…"):
            write_and_render(fp, lesson, questions)
        st.success("Saved and re-rendered.")
        st.rerun()


def render_generate_panel(fp: dict, slug: str) -> None:
    done = set(gen.get_lesson_status(fp)["done"])
    pending = next_pending_phase(fp)
    times = st.session_state.get("phase_times", {})

    # status row
    cols = st.columns([1, 1, 1, 1, 1, 1, 4])
    for i, key in enumerate(gen.PHASES):
        finished = key in done or (key == "p3" and fp["html_file"].exists())
        mark = "✅" if finished else ("🔵" if key == pending else "⬜")
        took = times.get(f"{slug}:{key}")
        cols[i].markdown(
            f"**{PHASE_LABELS[key]}**  \n{mark}"
            + (f"  \n<span style='font-size:11px;color:#666'>{took:.0f}s</span>" if took else ""),
            unsafe_allow_html=True)

    autorun_key = f"autorun_{slug}"
    fail_key = f"gen_err_{slug}"
    st.session_state.setdefault(fail_key, None)

    if pending is None:
        st.success("Generation complete.")
        return

    if not has_api_key():
        st.error("Generating needs `ANTHROPIC_API_KEY` in `.env`. Add it and restart the app.")
        return

    err = st.session_state[fail_key]
    if err:
        st.session_state[autorun_key] = False
        st.error(f"**{err['phase']}** failed: {err['message']}")
        st.caption(f"If a raw response was saved it is in `intermediate/{err['phase']}_debug.txt`.")

    label_for = PHASE_FUNCS.get(pending, (None, "Rendering"))[1]

    if st.session_state.get(autorun_key):
        c1, c2 = st.columns([3, 1])
        c1.info(f"**{label_for}** — this phase can take a few minutes. "
                f"Leave the tab open; each phase is saved as it finishes.")
        if c2.button("Stop", use_container_width=True):
            st.session_state[autorun_key] = False
            st.rerun()

        with st.spinner(f"{label_for}…"):
            from anthropic import Anthropic
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
            error = run_one_phase(fp, client, gen.load_prompts(PROMPTS_DIR), pending)
        st.session_state[fail_key] = error
        st.rerun()          # immediately picks up the next pending phase
        return

    start_label = ("Generate exit ticket" if not done
                   else f"Resume — next up: {label_for}")
    if st.button(start_label, type="primary"):
        st.session_state[fail_key] = None
        st.session_state[autorun_key] = True
        st.rerun()


# ── suggestions ───────────────────────────────────────────────────────────────
def render_finding(fp: dict, lesson: dict, questions: list, f: dict,
                   decided: dict) -> None:
    sev = f["severity"]
    head = f"{SEV_ICON.get(sev,'•')}  **{f['check']}**  ·  item {f['item']}  ·  _{SEV_WORD.get(sev,'')}_"
    with st.container(border=True):
        st.markdown(head)
        st.caption(f["reason"])

        if f.get("field") and f.get("current") is not None:
            st.markdown(f"`{f['field']}` currently:")
            st.code(f["current"], language=None)
        if f.get("proposed") is not None:
            st.markdown("proposed:")
            st.code(f["proposed"], language=None)

        prior = decided.get(f["id"])
        if prior:
            st.caption(f"{prior['action'].title()} on {prior['at']}"
                       + (f" — “{prior['note']}”" if prior.get("note") else ""))
            return

        c1, c2, c3 = st.columns([1, 1, 3])
        can_apply = bool(f.get("field")) and f.get("proposed") is not None
        if can_apply:
            if c1.button("Accept", key=f"acc_{f['id']}", type="primary"):
                if apply_patch(fp, lesson, questions, f["item"], f["field"], f["proposed"]):
                    save_decision(fp, f["id"], "accepted")
                    st.rerun()
                else:
                    st.error("Could not apply — the field may have changed since the check ran.")
        else:
            c1.caption("Fix by hand")
        if c2.button("Dismiss", key=f"rej_{f['id']}"):
            save_decision(fp, f["id"], "rejected",
                          st.session_state.get(f"note_{f['id']}", ""))
            st.rerun()
        c3.text_input("Note (optional — recorded in the QA report)",
                      key=f"note_{f['id']}", label_visibility="collapsed",
                      placeholder="Why you dismissed this, or what to do instead")


def render_suggestions_view(fp: dict, slug: str) -> None:
    if not fp["html_file"].exists():
        st.info("Generate the exit ticket first — suggestions run against the item set.")
        return

    lesson, questions = render_mod.parse_exit_ticket(
        fp["exit_ticket_final"].read_text(encoding="utf-8"))
    decided = load_decisions(fp)
    local = validate_mod.validate(lesson, questions)
    open_f = [f for f in local if f["id"] not in decided]
    closed_f = [f for f in local if f["id"] in decided]
    s = validate_mod.summarize(open_f)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Must fix", s["high"])
    c2.metric("Should fix", s["medium"])
    c3.metric("Style", s["low"])
    c4.metric("Dismissed", len(closed_f))

    st.markdown("#### Automatic checks")
    st.caption(
        "Arithmetic, answer-key consistency, choice ordering, duplicate and repeated "
        "choices, rationale house style and LaTeX validity. These run free on every save."
    )
    if not open_f:
        st.success("No open findings from the automatic checks.")
    for f in open_f:
        render_finding(fp, lesson, questions, f, decided)

    if closed_f:
        with st.expander(f"Dismissed ({len(closed_f)})"):
            for f in closed_f:
                render_finding(fp, lesson, questions, f, decided)

    st.divider()
    st.markdown("#### Model review")
    st.caption(
        "An independent math check plus the full rubric review. Run this while you are "
        "still authoring — it no longer requires approving first."
    )
    render_model_review_controls(fp, slug, lesson, questions)


def render_model_review_controls(fp: dict, slug: str, lesson: dict, questions: list) -> None:
    if not has_api_key():
        st.error("The model review needs `ANTHROPIC_API_KEY` in `.env`.")
        return

    done = fp["review_report"].exists()
    err_key = f"rev_err_{slug}"
    st.session_state.setdefault(err_key, None)
    if st.session_state[err_key]:
        e = st.session_state[err_key]
        st.error(f"**{e['step']}** failed: {e['message']}")

    if done:
        stale = fp["exit_ticket_final"].stat().st_mtime > fp["review_report"].stat().st_mtime
        when = datetime.datetime.fromtimestamp(
            fp["review_report"].stat().st_mtime).strftime("%b %d, %I:%M %p")
        if stale:
            st.warning(f"The last review ran {when}, before your most recent edit — "
                       f"its findings may no longer match these items.")
        else:
            st.success(f"Review is current, run {when}.")

    label = "Run model review" if not done else "Re-run model review"
    if st.button(label, type="primary" if not done else "secondary"):
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        prompts = review_mod.load_review_prompts(PROMPTS_DIR)
        profile = (fp["lesson_profile"].read_text(encoding="utf-8")
                   if fp["lesson_profile"].exists() else "")
        images, skipped = review_mod.gather_item_images(fp, questions)
        if skipped:
            st.info("Some visuals could not be attached as images; the review will use ALT text.")
        st.session_state[err_key] = None

        with st.spinner("Math check…"):
            try:
                math_text = review_mod.run_math_check(
                    fp, client, prompts, lesson, questions, images=images)
            except ValueError as e:
                st.session_state[err_key] = {"step": "Math check", "message": str(e)}
                st.rerun()
        with st.spinner("Rubric review…"):
            try:
                review_mod.run_rubric_review(
                    fp, client, prompts, profile, math_text, lesson, questions, images=images)
            except ValueError as e:
                st.session_state[err_key] = {"step": "Rubric review", "message": str(e)}
                st.rerun()
        archive_report(fp)
        st.session_state["_pending_view"] = "QA report"
        st.rerun()


# ── preview ───────────────────────────────────────────────────────────────────
def render_preview_view(fp: dict, questions: list | None = None) -> None:
    if not fp["html_file"].exists():
        st.info("Nothing rendered yet.")
        return
    html = fp["html_file"].read_text(encoding="utf-8")
    components.html(html, height=1200, scrolling=True)
    if questions is None:
        _, questions = render_mod.parse_exit_ticket(
            fp["exit_ticket_final"].read_text(encoding="utf-8"))
    if any(q.get("visual") for q in questions):
        with st.expander("Download visuals"):
            if not png_export.png_available():
                st.caption(png_export.png_unavailable_reason())
            for q in questions:
                if not q.get("visual"):
                    continue
                svg = fp["visuals_dir"] / f"q{q['id']}_visual.svg"
                png = fp["visuals_dir"] / f"q{q['id']}_visual.png"
                cols = st.columns([1, 2, 2])
                cols[0].markdown(f"Q{q['id']}")
                if svg.exists():
                    cols[1].download_button("SVG", svg.read_bytes(), svg.name,
                                            "image/svg+xml", key=f"svg{q['id']}")
                if png.exists():
                    cols[2].download_button("PNG", png.read_bytes(), png.name,
                                            "image/png", key=f"png{q['id']}")


# ── QA report ─────────────────────────────────────────────────────────────────
def archive_report(fp: dict) -> None:
    """Keep every review, not just the latest — the report is an audit record,
    so a re-run must not erase what a previous run said."""
    if not fp["review_report"].exists():
        return
    hist = extra_paths(fp)["report_history"]
    hist.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    (hist / f"review_report_{stamp}.html").write_text(
        fp["review_report"].read_text(encoding="utf-8"), encoding="utf-8")


def report_filename(identity: dict, slug: str, kind: str) -> str:
    bits = [
        (identity.get("curriculum_version") or "").strip().lower().replace(" ", "-"),
        f"grade{(identity.get('grade') or '').strip()}",
        f"unit{(identity.get('unit') or '').strip()}",
        f"lesson{(identity.get('lesson_number') or '').strip()}",
    ]
    stem = "-".join(b for b in bits if b and not b.endswith("None")) or slug
    return f"{stem}-{kind}.html"


def render_report_view(fp: dict, slug: str, identity: dict) -> None:
    c1, c2 = st.columns([3, 1])
    c1.markdown("#### QA report")
    if c2.button("✏️  Edit items", use_container_width=True):
        st.session_state["_pending_view"] = "Items"
        st.rerun()

    if not fp["review_report"].exists():
        st.info("No report yet. Run the model review from the Suggestions tab.")
        return

    stale = fp["exit_ticket_final"].stat().st_mtime > fp["review_report"].stat().st_mtime
    if stale:
        st.warning("These items have been edited since this report was generated. "
                   "Re-run the model review to produce a report that matches them.")

    html = fp["review_report"].read_text(encoding="utf-8")
    d1, d2 = st.columns(2)
    d1.download_button("Download QA report", html,
                       report_filename(identity, slug, "qa-report"),
                       "text/html", use_container_width=True)
    if fp["html_file"].exists():
        d2.download_button("Download exit ticket", fp["html_file"].read_text(encoding="utf-8"),
                           report_filename(identity, slug, "exit-ticket"),
                           "text/html", use_container_width=True)

    decided = load_decisions(fp)
    if decided:
        with st.expander(f"Decisions recorded on findings ({len(decided)})"):
            for fid, d in sorted(decided.items(), key=lambda kv: kv[1]["at"], reverse=True):
                st.markdown(f"- **{d['action'].title()}** · {d['at']}"
                            + (f" — {d['note']}" if d.get("note") else ""))

    hist = sorted(extra_paths(fp)["report_history"].glob("review_report_*.html"), reverse=True)
    if len(hist) > 1:
        with st.expander(f"Earlier reports ({len(hist) - 1})"):
            for h in hist[1:]:
                st.download_button(h.stem.replace("review_report_", "Report from "),
                                   h.read_text(encoding="utf-8"), h.name,
                                   "text/html", key=f"h_{h.name}")

    components.html(html, height=1400, scrolling=True)


# ── workspace ─────────────────────────────────────────────────────────────────
def render_workspace(fp: dict, slug: str, identity: dict) -> None:
    rows = [r for r in lesson_index() if r["slug"] == slug]
    row = rows[0] if rows else {"approved": gen.is_approved(fp),
                                "reviewed": fp["review_report"].exists(),
                                "rendered": fp["html_file"].exists()}
    status = status_of(row)

    title = f"Lesson {identity.get('lesson_number','')}: {identity.get('lesson_title','')}".strip(": ")
    st.subheader(f"{STATUS_ICON[status]}  {title or slug}")
    st.caption(
        f"{identity.get('curriculum_version','')} · Grade {identity.get('grade','')} · "
        f"Unit {identity.get('unit','')} · {', '.join(identity.get('standards', []))} · "
        f"**{status}**"
    )

    if eval_mod.is_evaluation(fp):
        info = eval_mod.evaluation_info(fp)
        st.caption(
            f"📄 Evaluation — items extracted from `{info.get('pdf_name', 'a PDF')}`"
            + (f" ({info.get('items')} items)" if info.get("items") else "")
            + ". Nothing here rewrites them; the review reports on them as written."
        )
        extracted = fp["intermediate_dir"] / "extracted_items.xml"
        if extracted.exists():
            note = eval_mod.extraction_note(extracted.read_text(encoding="utf-8"))
            if note:
                st.warning(f"**Extraction flagged uncertainty:** {note}")

    if st.session_state.pop("_just_approved", False):
        st.success(
            "Approved and filed under **Finished**. Use ＋ New lesson in the sidebar to "
            "start the next one, or switch the Stage selector back to In progress."
        )

    if st.session_state.pop("_approval_cleared", False):
        st.info("This lesson was approved before your edit, so the approval was cleared. "
                "Re-approve once you're happy with the changes.")

    pending_view = st.session_state.pop("_pending_view", None)
    if pending_view in VIEWS:
        st.session_state["view"] = pending_view
    st.session_state.setdefault("view", "Items")

    open_high = 0
    if fp["html_file"].exists():
        lesson_i, questions_i = render_mod.parse_exit_ticket(
            fp["exit_ticket_final"].read_text(encoding="utf-8"))
        decided = load_decisions(fp)
        open_high = sum(1 for f in validate_mod.validate(lesson_i, questions_i)
                        if f["severity"] == "high" and f["id"] not in decided)

    def label(v: str) -> str:
        if v == "Suggestions" and open_high:
            return f"Suggestions  🔴{open_high}"
        return v

    st.radio("view", VIEWS, horizontal=True, key="view",
             format_func=label, label_visibility="collapsed")
    view = st.session_state["view"]
    st.divider()

    if view == "Items":
        render_items_view(fp, slug, identity)
    elif view == "Suggestions":
        render_suggestions_view(fp, slug)
    elif view == "Preview":
        render_preview_view(fp)
    else:
        render_report_view(fp, slug, identity)

    # sign-off
    if fp["html_file"].exists():
        st.divider()
        if gen.is_approved(fp):
            st.success("Approved. Editing any field will clear this approval.")
            if st.button("Withdraw approval"):
                fp["approved_json"].rename(fp["approved_json"].with_suffix(".json.withdrawn"))
                st.session_state["_pending_stage"] = STAGE_ACTIVE
                st.session_state["_pending_slug"] = slug
                st.rerun()
        else:
            if open_high:
                st.caption(f"{open_high} must-fix finding(s) still open. "
                           f"You can approve anyway, but the report will record them.")
            if st.button("Approve — sign off on this item set", type="primary"):
                gen.mark_approved(fp)
                st.session_state["_pending_stage"] = STAGE_DONE
                st.session_state["_pending_slug"] = slug
                st.session_state["_just_approved"] = True
                st.rerun()


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    st.title("📝 ANet Exit Ticket Studio")
    _run_startup_checks()

    render_mode_toggle()
    profile = render_profile_picker()
    if profile is None:
        name = st.session_state.pop("_new_profile_name", None)
        if name:
            st.success(f"Profile created for {name} — pick it from the dropdown to start.")
        st.info("Pick your name in the sidebar, or add a profile, to open your workspace.")
        return

    adopted = st.session_state.pop("_adopted", None)
    if adopted:
        st.success(f"Moved {len(adopted)} lesson(s) into your workspace: {', '.join(adopted)}")

    selected = render_library()
    if selected == NEW_LESSON:
        if current_mode() == MODE_EVAL:
            render_new_evaluation()
        else:
            render_new_lesson()
        return

    fp = gen.get_lesson_paths(workspace(), selected)
    identity = _read_identity(fp["output_dir"])
    if identity is None:
        st.error(f"`{fp['output_dir']}` has no readable `identity.json`.")
        return
    render_workspace(fp, selected, identity)


main()
