# ANet Content Gen QA

Authors ANet/Atlas-style math Exit Ticket items from a Kiddom lesson export, and reviews
them — either items it generated itself, or items authored elsewhere and handed over as a
PDF. Everything happens in one local Streamlit app: authoring, automatic checking, the
review passes, and the QA report that comes out the other end.

The point of the tool is that **review happens while you author**, not as a separate
handoff afterwards. Mechanical defects are caught in code, instantly and for free. The
model reviews run on demand. Approving is the sign-off at the end, not a gate you pass
before anyone looks at the work.

---

## Quick start

```bash
cd anet-content-gen-qa
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # then put your Anthropic API key in it
streamlit run app.py
```

Your key goes in `.env` as `ANTHROPIC_API_KEY=sk-ant-api03-...`. Get one from
[console.anthropic.com](https://console.anthropic.com) → Settings → API keys; the full
secret is shown only once, at creation. Console billing is separate from a Claude.ai
subscription.

There are `setup.sh` / `launch.command` helpers, but on a managed Mac macOS Gatekeeper may
refuse to execute them because they arrived as downloaded files. If that happens, don't
fight it — type the commands above directly into Terminal instead. They do the same thing.

**No key?** The app still runs. Editing, the automatic checks, rendering and the report
viewer all work offline. Only generation, the model review and PDF extraction need the key.

---

## The two modes

A toggle at the top of the sidebar picks which kind of work you're doing. Each keeps its
own library, so authored lessons and evaluated sets don't mix.

**Create items.** Upload a Kiddom Teacher Edition export (Student Edition optional but
useful for confirming exact student-facing phrasing). The app reads the lesson's identity
straight out of the document header — curriculum, grade, unit, lesson number and title,
standard codes — and asks you to confirm it. Then it runs the generation pipeline: extract
a structured lesson profile, plan three items, write them, review the content, review the
language and bias, render to HTML with KaTeX and any visuals.

**Evaluate items.** Upload a PDF of items authored anywhere else — ACT, a Gemini gem, a
Word doc — plus the Kiddom export for the lesson they were written for. The app reads the
lesson (it needs the profile to judge alignment, scope, number range and vocabulary
against), extracts the items from the PDF into its own schema, and renders them. From
there an evaluated set behaves exactly like an authored one and gets the same checks and
reviews. Extraction is deliberately faithful: a wrong item is extracted exactly as wrong
as it is, because silently fixing it would hide the defect from the people who need to see
it. Phases 2c and 2d, which rewrite items, do not run in this mode.

---

## Working on a lesson

Each lesson opens as one workspace with four views you can move between freely.

**Items** — every field editable: stem, prompt, the four choices, which one is correct, and
each rationale. Saving re-renders the preview and re-runs the checks. Editing is available
at every status, including after a report exists and after approval.

**Suggestions** — one queue, two sources. The automatic checks (`pipeline/validate.py`) run
in code on every save, cost nothing, and cover arithmetic, answer-key consistency, the
answer being visible in its own stem, duplicate and equivalent choices, choice ordering,
distractor values reused across items, rationale house style, and LaTeX validity. The model
review — an independent math check plus the full rubric review — runs when you ask for it.
Findings carry a severity, and where a fix is computable there's an Accept button that
writes that one field and re-renders. Dismissing a finding records your reason.

**Preview** — the rendered exit ticket as a student would see it.

**QA report** — the shareable review record. Every run is archived under
`output/<person>/<lesson>/review/history/`, so re-reviewing never overwrites what a previous
run said, and your Accept/Dismiss decisions are recorded alongside it.

Approving files the set under **Finished** in the library. Editing an approved lesson clears
the approval rather than letting a sign-off describe items that have since changed.

---

## Workspaces

Everyone works in the same content library but keeps their own workspace. Pick your name
from the dropdown, or add it once via **＋ Add profile**; names are stored once and matched
case-insensitively, so `Mikayla` and `mikayla` are the same person.

**This is separation and attribution, not access control.** The roster is a plain list and
anyone using the app can select any name on it. That is fine for a collaborating team that
wants its own desks. If you deploy this somewhere shared and need people to genuinely not
be able to see each other's work, that requires real sign-in — a name dropdown will not do
it, and shouldn't be described as if it does.

---

## Where things live

```
output/
  profiles.json                       the roster
  <person>/
    <state>-grade<n>-unit<n>-lesson<n>/
      identity.json                   confirmed lesson identity
      uploaded_te.md, uploaded_se.md  the exports, saved as-is
      source_items.pdf                evaluation mode only
      evaluation.json                 marks the set as evaluated, not authored
      approved.json                   present once signed off
      intermediate/
        lesson_profile.txt            Phase 1
        item_plan.xml                 Phase 2a
        exit_ticket_raw.xml           Phase 2b
        exit_ticket_reviewed.xml      Phase 2c
        exit_ticket.xml               Phase 2d — what the editor works on
        extracted_items.xml           evaluation mode: the PDF as extracted
      visuals/                        per-question SVG (and PNG where available)
      exit_ticket.html                the rendered preview
      review/
        math_check_output.txt
        review_report.html            the QA report
        history/                      every previous report, timestamped
        decisions.json                Accept/Dismiss decisions and notes
```

Each phase writes its own file, which is what makes generation resumable: if a phase fails
or the connection drops, re-running only redoes what's missing.

---

## Code layout

- `app.py` — every Streamlit call and all session state.
- `pipeline/generation.py` — Phases 1 and 2a–2d (model calls).
- `pipeline/render.py` — parsing and HTML rendering. No API calls.
- `pipeline/validate.py` — the automatic checks. No API calls.
- `pipeline/review.py` — the math check and rubric review.
- `pipeline/evaluate.py` — PDF extraction for evaluation mode.
- `pipeline/profiles.py` — workspaces.
- `pipeline/identity_detect.py` — deterministic lesson identity from a document header.
- `visual_renderers.py` — the visual type registry.
- `prompts/` — one file per phase. These are the product; the Python is plumbing.
  `_ref_*.md` files are the original reference prompts, kept for provenance.

The prompt files are where behaviour actually lives. If generated items are wrong in a
consistent way, the fix is almost always in a prompt, not in the code.

---

## Known limitations

**Every generated item is a draft.** Nothing this app produces — including a review that
comes back clean — should be treated as ANet-final without a human's own read. AI-assisted
content needs meaningful human revision before it is ANet IP.

**One lesson at a time.** The review-and-edit step is inherently one person, one lesson. The
app doesn't batch-process unattended.

**VA/MD/GA standards aren't decomposed.** A state standard code is treated as a label, not
parsed into assessable parts the way CCSS codes are. The lesson content is the primary
source either way.

**PNG export is optional.** SVG visuals always work. PNG additionally needs Cairo
(`brew install cairo`, or `apt install libcairo2`); without it the app simply doesn't offer
PNG downloads.

**The automatic checks are mechanical, not editorial.** They catch arithmetic, consistency
and formatting. They cannot tell you whether an item is worth asking.
