# Prompt 1 — Lesson Extraction (adapted for anet-exit-ticket-studio)

### Extract a structured lesson profile from a Kiddom lesson Markdown export

Adapted from the team's original `prompt_1_extract_v3.md`. Two changes from that version,
both driven by this app's own I/O:

1. **Input is a Kiddom TE/SE Markdown export**, uploaded directly in the app — not a lesson
   PDF attached in a chat. There are no images to read as separate attachments; any visuals
   in a Kiddom export appear inline as Markdown image syntax (`![alt](path)`) or as a plain
   text description. STEP 3B below is rewritten around that. Many lessons — especially
   number/equation-only ones — have no student-facing visuals at all, and that is a normal,
   expected result, not a missed extraction.
2. **Lesson identity (curriculum version / state, grade, unit, lesson number and title,
   and lesson-level standard code) is auto-detected by the app itself** — deterministically,
   from the document's own header — and confirmed by the user *before* this prompt runs.
   Confirmed values are substituted into the `{{LESSON_IDENTITY}}` block below rather than
   re-derived here. Your job in STEP 1 is to verify they're consistent with what the
   document's body actually says (they should be — flag it if not) and to find every
   *additional* standard code that appears deeper in the lesson (a warm-up or cool-down can
   carry a different or additional tag than the lesson-level one).

---

## Inputs provided to you

**Confirmed lesson identity** (detected from the document header, confirmed by the user in
the app before this step ran):

```
{{LESSON_IDENTITY}}
```

**Lesson document(s):**

```
{{LESSON_MARKDOWN}}
```

(If both a Teacher Edition and a Student Edition were uploaded, both are included above,
clearly separated. The Teacher Edition is the primary source — it carries the
"Advancing/Responding to Student Thinking" notes that Student Edition exports omit. Use the
Student Edition only to confirm exact student-facing phrasing where it differs from the
Teacher Edition's paraphrase of it.)

---

## How to read this document

You are an expert curriculum analyst specializing in grades K–8 math assessment. Read the
lesson document(s) above carefully and extract a complete, structured lesson profile that
will be used to write high-quality Exit Ticket questions in ANet's Atlas style.

Work through the extraction steps below in order. Be precise and conservative — only
include what is explicitly stated or clearly demonstrated in the lesson. Do not infer,
generalize, or add content from outside the document. If the embedded sample answer to a
cool-down or activity question looks wrong when you check it yourself, say so explicitly in
STEP 3A rather than passing it through as fact — lesson materials are not infallible (see
`lesson-input-schema.md`'s "Verify, don't trust, embedded sample answers").

**The cool-down is the primary calibration anchor** — closer in grain, difficulty, and
scope to a generated Exit Ticket item than any other part of the lesson. Match its number
ranges and item shapes before anything else drawn from earlier activities.

---

## STEP 1 — LESSON IDENTITY

Start from the confirmed identity block above. Then, scanning the full document:

**Lesson title:** (should match the confirmed block — flag any mismatch)
**Curriculum version (state / National / IM 360):** (should match the confirmed block)
**Grade level:** (should match the confirmed block)
**Unit:** (should match the confirmed block)
**Lesson-level standard(s):** (should match the confirmed block's standards)
**All other standard codes found anywhere in the document**, with where each appears (e.g.
"Warm-up: 3.CE.1.c — differs from the lesson-level tag, spiral review"; "Cool-down:
3.CE.1.d — matches lesson-level tag"). A single lesson can carry more than one standard at
different depths — extract all of them and keep their location; don't collapse to one code.
**Lesson duration:** [total time if stated, or sum of each timed section]

If anything in this step doesn't match the confirmed identity block, say so plainly at the
top of your output — the app surfaces this as a warning rather than silently overriding
what the user confirmed.

---

## STEP 2 — LEARNING GOALS AND TARGETS

**A. Teacher-facing learning goals**
List every learning goal stated in the lesson. Copy them exactly — do not paraphrase.

**B. Student-facing learning targets**
List every student-facing target ("Let's..." / "I can..." statements, one per activity
section) exactly as written. Kiddom exports usually restate this per-activity, not just
once at the lesson level — capture each one and which activity it belongs to.

**C. Primary focus of this lesson**
In 2–3 sentences, describe what this lesson is primarily about based on the lesson
narrative. What is the central concept or skill students are building? What is the "why"
behind the lesson sequence?

**D. What this lesson is NOT about**
List any concepts or skills that are explicitly described as out of scope, saved for future
lessons, or intentionally avoided in this lesson. Include any language from the teacher
notes such as "students will explore this further in…" or "this lesson focuses on X rather
than Y."

---

## STEP 3 — ACTIVITY ANALYSIS

For each activity in the lesson (warm-up, main activities, cool-down), complete both parts
below — **3A (text-based)** and **3B (visual-based)** — before moving to the next activity.
If a field is not present for an activity, write "not stated."

### Part 3A — Text analysis

**Activity name:**
**Time:**
**Instructional routine, if named:** (e.g. "Number Talk," "Find Your Match" partner card
matching, a "true or false" launch — Kiddom exports often name these explicitly; carry the
name through, since a generated item can legitimately be framed as the assessment version
of a named routine)
**Purpose:** [What is the specific mathematical goal of this activity?]
**Key question or task:** [The central problem or prompt students work on]
**Representations used:** [number lines, tables, graphs, diagrams, equations, real-world
contexts, etc.]
**Number types and values used:** [integers, fractions, decimals, negatives — and the
specific range or examples used in the text]
**Vocabulary used:** [all math terms used or introduced in this activity, plus notation
conventions — e.g. does the lesson use "=" / "≠" or spell out "equal to" / "not equal to"?]
**Embedded practice questions:** copy each one verbatim, with its stated point value and
item type (Multiple Choice / Short Answer / Written Response), and its key or sample
response if given. Independently verify any sample response's arithmetic — flag a mismatch
rather than passing it through (see the cool-down note above; this applies to every
activity, not just the cool-down).
**Instructional notes relevant to assessment:** Scan the following sub-sections explicitly
— each is a high-value source of misconception data:
- **"Advancing Student Thinking" / "Advancing Student Work":** Copy the exact description of
  what teachers should do when students struggle. These sections name the specific error a
  student is making.
- **"Responding to Student Thinking":** Copy any described wrong answer patterns or
  intervention guidance — Kiddom cool-downs usually carry this field explicitly.
- **Activity synthesis discussion questions:** Note any question that addresses a specific
  wrong answer or confusion, especially lines that begin "if not mentioned by students…" or
  "ask students who…"
- **Named wrong student answers:** If the lesson narrative mentions a specific incorrect
  value, expression, or reasoning a student might produce, copy it exactly with the
  incorrect value highlighted.
- **"Next-day supports":** note if present — not misconception data itself, but confirms
  what the lesson considers unresolved/worth revisiting, which is a signal the cool-down's
  skill is exactly where this lesson expects lingering difficulty.

For each note, record: the source sub-section, the activity it belongs to, and — crucially
— the specific wrong answer or error behavior the student would exhibit (as concrete as
possible, including incorrect numerical values where the materials provide them).

### Part 3B — Visual analysis

Kiddom Markdown exports represent visuals two ways: inline Markdown image syntax
(`![alt text](path)`) with little to no additional description, or a plain-text description
of a diagram embedded directly in the activity text (e.g. "a number line from -5 to 5 with
a point at -3"). Scan for both. **Many lessons — anything primarily about equations,
computation, or symbolic reasoning — have no student-facing visuals at all. If you find
none, write "No student-facing visuals in this lesson" once and move on; do not force an
entry.** Only analyze visuals that are part of a student-facing task or assessment item —
skip decorative images and teacher-only diagrams.

For each student-facing visual found:

**Visual description:** [one sentence: what type of visual is it and what does it show]
**Visual type:** [e.g., horizontal number line, vertical number line, coordinate plane,
table, bar model, tape diagram, box plot, thermometer, etc.]
**Orientation:** [horizontal / vertical / other]
**Labeled values and range:** [list every number or label explicitly shown or described —
e.g., "tick marks labeled −5 to 5 by 1s"]
**Unlabeled elements:** [describe any tick marks, grid lines, or intervals present but not
labeled]
**Point or value placement:** [are any points, dots, or markers shown? If so, do they fall
exactly on a labeled tick mark, on an unlabeled tick mark, or between tick marks?]
**Values visible in the visual but absent from surrounding text:** [list any numbers or
positions that appear only in the visual's alt text/description, not in the written task]
**Complexity level:** [simple / moderate / complex — and one sentence justifying the rating]

Repeat Part 3A and Part 3B for every activity, including the cool-down.

---

## STEP 4 — ASSESSMENT PROFILE

Using everything extracted above, produce the following summary. This is the structured
profile passed directly to the item planner (Prompt 2a). Every field must be grounded in
what you extracted in Steps 1–3 — do not add anything new here.

---

### STRUCTURED LESSON PROFILE

**Lesson title:**
**Curriculum version:**
**Grade:**
**Unit:**
**Lesson number:**
**Standards:** [lesson-level, plus every other code found and where]

**All learning goals in this lesson (copy exactly from Step 2A — do not paraphrase or
reduce):**
[List every learning goal found. Number them. There may be 2, 3, 4, or more — list all of
them.]

**Ranked by centrality to this lesson's narrative and activities:**
[Re-order the list above from most central to least central. One sentence per goal
explaining why it ranks where it does, grounded in the lesson narrative, activity sequence,
or teacher notes.]

**Assessment candidacy — for each goal, note one of the following:**
- Strong MC candidate: the skill or concept can be fairly and fully assessed with a single
  multiple choice question
- Weak MC candidate: the goal involves a process, construction, or open-ended reasoning that
  does not reduce well to a single multiple choice question — note why (e.g., "requires
  student to construct a number line," "requires explaining reasoning," "too broad to
  assess in one item")

For each goal, also document:
- **Visual necessity rating:** Choose one — `Required` (use when EITHER: (a) the question
  would be ambiguous or impossible without a visual, OR (b) the construct involves
  distinguishing between two or more options that are both valid for the same input — in
  multiple choice format, a student could keyword-match the correct answer from the prompt
  text without genuinely evaluating the options; a visual showing both applied to the same
  context is the only way to assess real understanding rather than recall), `Supported` (a
  visual would strengthen the question but the construct can stand alone in text — use only
  when every wrong answer choice is obviously inapplicable from the text description
  alone), or `Text-only` (no visual is needed or useful for this construct)
- **Best visual type for this construct:** Name the specific visual type from the permitted
  representations list that best serves MC assessment of this construct (e.g.,
  `box_plot_comparative`, `number_line_h`). If the construct is `Text-only`, write "none."
  This does not commit Prompt 2a to using a visual — it is a recommendation based on what
  the lesson uses and what would be fair. **If this lesson had no student-facing visuals at
  all (Step 3B found none), every goal defaults to `Text-only` unless the construct itself
  genuinely requires one that the lesson simply didn't happen to use** — say so explicitly
  rather than inventing a visual tradition this lesson doesn't have.

[The item planner will use this field to select 3 constructs. If fewer than 3 goals are
strong MC candidates, flag this clearly so the writer knows to work within that constraint.]

**Key vocabulary that must or may appear in exit ticket items:**
[List terms students have seen in this lesson and are expected to use or recognize —
including notation conventions, e.g. "=" / "≠" vs. spelled-out "equal to."]

**Permitted number types and value ranges:**
[Be specific — e.g., "integers only, range −10 to 10" or "positive and negative decimals to
the tenths place." Ground this in both the text and the visual analysis, using the cool-down
range as the primary anchor — use the more restrictive of cool-down vs. earlier activities
if they differ.]

**Permitted representations and contexts:**
[List the specific diagram types, real-world contexts, and representations used in
student-facing tasks. Only include representations that appeared in student-facing
activities — not teacher-only materials. If none, say so.]

**Difficulty calibration:**
[Describe the difficulty level of the lesson's cool-down, including whether values fall on
or between tick marks (if visuals are present), how much reading or interpretation is
required, and how many steps a student must take. Exit ticket items should match this level
— not easier, not harder.]

**Language and phrasing patterns to follow:**
[Note specific phrasing the lesson uses that exit ticket items should mirror — e.g., "same
distance from 0," symbol vs. word conventions. Copy phrases exactly from the lesson.]

**Visual conventions and constraints:**
[Synthesized from all visual analyses in Step 3B. If the lesson has no student-facing
visuals, write "No visual convention established by this lesson — a generated item should
default to Text-only unless a construct's Visual necessity rating above is Required." If it
does, specify:]
- Permitted visual types: [list only the types that appeared in student-facing tasks]
- Orientation convention: [horizontal / vertical / both — and which was used in which
  activity types]
- Scale and range in use: [the actual ranges shown in student-facing visuals, not just what
  the text describes]
- Labeled vs. unlabeled tick marks: [what proportion of tick marks were labeled in
  student-facing tasks]
- Point placement convention: [labeled tick marks, unlabeled tick marks, or between tick
  marks — and at what difficulty level each appeared]
- Complexity ceiling: [the most complex visual used in a student-facing task — exit ticket
  visuals must not exceed this]
- Values to avoid: [any specific values or configurations that appeared only in
  teacher-facing materials and should not appear in student-facing exit ticket items]

**Prerequisite prior knowledge assumed by this lesson:**
List every prior skill or concept the lesson explicitly states or clearly implies students
should already know before this lesson. Draw from narrative phrases like "in the previous
lesson, students were introduced to…" and activity launch instructions. For each item:
- **Skill/concept:** [name it concisely]
- **Source:** [where in the lesson materials it is stated or implied]

If the lesson materials state no prerequisites explicitly, write: "No prerequisites
explicitly stated — standard prerequisite skills for this grade band assumed (e.g.,
arithmetic operations, basic fraction concepts)."

This field is used by the content and bias review steps to evaluate whether any item
requires knowledge that is neither taught in this lesson nor a stated prerequisite.

---

**What to EXCLUDE from exit ticket items:**
- Concepts not yet taught:
- Number types not used in this lesson:
- Representations not used in student-facing tasks:
- Vocabulary not introduced in this lesson:
- Visual configurations not used in student-facing tasks:

**Misconception signals from teacher notes:**
Using the instructional notes collected in Step 3A for every activity, produce one numbered
entry per misconception signal found. Each entry has four sub-fields:

**Signal [N]:**
- **Source:** activity name and sub-section (e.g., "Activity 2 — Advancing Student
  Thinking")
- **Error description:** one sentence on exactly what the student does wrong — the specific
  incorrect action or reasoning, not the abstract concept gap
- **Wrong answer produced:** the specific incorrect value, expression, or graph the student
  would produce. Copy verbatim from the lesson if named; derive it from the described error
  if not
- **Priority:** High (lesson names a specific wrong answer explicitly) / Medium (error
  pattern described but no specific value given) / Low (implied by lesson structure, not
  explicitly named)

Repeat this block for every signal found. Number them Signal 1, Signal 2, etc.

These signals feed directly into the item planner's distractor planning. High-priority
signals must appear as planned misconceptions for the relevant construct.

**Cool-down questions (copy exactly):**
[Copy the cool-down questions word for word, including any answer choices, values, and
visual descriptions. These are the closest model for exit ticket difficulty, style, and
visual complexity. Note independently-verified arithmetic for every key/sample response —
flag any that don't check out (see the note at the top of this prompt).]

---

Output only the STRUCTURED LESSON PROFILE from Step 4, preceded by any identity mismatch
warning from Step 1 if one exists. Do not include your other working notes from Steps 1–3 in
the final output — those are for your internal reasoning only.

---

*Prompt 1 of the anet-exit-ticket-studio pipeline. Output feeds directly into
`prompt_2a_define.md` — Item Planner.*
