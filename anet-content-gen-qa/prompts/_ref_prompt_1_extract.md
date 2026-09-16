# Prompt 1 — Lesson Extraction
### Extract a structured lesson profile from a lesson PDF

---

## How to use this prompt

Paste this prompt into a new conversation and attach the lesson PDF. Review the output carefully before passing it to Prompt 2. Correct any errors or missing fields before proceeding — this profile is the foundation for all 3 exit ticket questions.

---

## The Prompt

---

You are an expert curriculum analyst specializing in grades 3–8 math assessment. A lesson document has been attached. Your job is to read it carefully — including all images, diagrams, and visuals — and extract a complete, structured lesson profile that will be used to write high-quality exit ticket questions.

Work through the four extraction steps below in order. Be precise and conservative — only include what is explicitly stated or clearly demonstrated in the lesson. Do not infer, generalize, or add content from outside the document.

---

## STEP 1 — LESSON IDENTITY

Extract the following fields exactly as they appear in the document:

**Lesson title:**
**Grade level:**
**Unit:**
**Standards addressed:** [list every standard code referenced]
**Lesson duration:** [total time if stated]

---

## STEP 2 — LEARNING GOALS AND TARGETS

**A. Teacher-facing learning goals**
List every learning goal stated in the lesson. Copy them exactly — do not paraphrase.

**B. Student-facing learning targets**
List every student-facing target ("I can…" statements) exactly as written.

**C. Primary focus of this lesson**
In 2–3 sentences, describe what this lesson is primarily about based on the lesson narrative. What is the central concept or skill students are building? What is the "why" behind the lesson sequence?

**D. What this lesson is NOT about**
List any concepts or skills that are explicitly described as out of scope, saved for future lessons, or intentionally avoided in this lesson. Include any language from the teacher notes such as "students will explore this further in…" or "this lesson focuses on X rather than Y."

---

## STEP 3 — ACTIVITY ANALYSIS

For each activity in the lesson (warm-up, main activities, cool-down), complete both parts below — **3A (text-based)** and **3B (image-based)** — before moving to the next activity. If a field is not present for an activity, write "not stated."

### Part 3A — Text analysis

**Activity name:**
**Time:**
**Purpose:** [What is the specific mathematical goal of this activity?]
**Key question or task:** [The central problem or prompt students work on]
**Representations used:** [number lines, tables, graphs, diagrams, equations, real-world contexts, etc.]
**Number types and values used:** [integers, fractions, decimals, negatives — and the specific range or examples used in the text]
**Vocabulary used:** [all math terms used or introduced in this activity]
**Instructional notes relevant to assessment:** Scan the following sub-sections explicitly — each is a high-value source of misconception data:
- **"Building On" / "Required Prior Knowledge" / narrative phrases like "students have previously learned," "this lesson extends," "building on their understanding of":** Copy any stated prior knowledge the lesson assumes students already have. This becomes the prerequisite prior knowledge field in Step 4 and anchors the unfair prior content checks in later prompts.
- **"Addressing Standards" / "Building Towards":** Note the current standard and any explicitly stated standards the lesson builds toward. This helps determine what is future content vs. current content.
- **"Advancing Student Thinking" / "Advancing Student Work":** Copy the exact description of what teachers should do when students struggle. These sections name the specific error a student is making.
- **"Responding to Student Thinking":** Copy any described wrong answer patterns or intervention guidance.
- **Monitor/Notice notes ("Notice students who…"):** Copy verbatim. These flag live errors teachers are told to watch for during the activity.
- **Activity synthesis discussion questions:** Note any question that addresses a specific wrong answer or confusion, especially lines that begin "if not mentioned by students…" or "ask students who…"
- **Named wrong student answers:** If the lesson narrative mentions a specific incorrect value, expression, or reasoning a student might produce (e.g., "Some students may say −2.5 because…"), copy it exactly with the incorrect value highlighted.
For each note, record: the source sub-section, the activity it belongs to, and — crucially — the specific wrong answer or error behavior the student would exhibit (as concrete as possible, including incorrect numerical values where the materials provide them).

### Part 3B — Image analysis

Examine every image, diagram, or visual that appears in this activity. For each one, answer the following. Only analyze images that are part of a **student-facing task or assessment item** — skip decorative images, real-world photo contexts, and teacher-only diagrams.

For each student-facing image:

**Image description:** [one sentence: what type of visual is it and what does it show]
**Visual type:** [e.g., horizontal number line, vertical number line, coordinate plane, table, bar model, tape diagram, thermometer, etc.]
**Orientation:** [horizontal / vertical / other]
**Labeled values and range:** [list every number or label explicitly shown — e.g., "tick marks labeled −5 to 5 by 1s" or "thermometer labeled −4 to 5 by 1s with a tick mark between each integer"]
**Unlabeled elements:** [describe any tick marks, grid lines, or intervals that are present but not labeled — e.g., "one unlabeled tick mark between each integer"]
**Point or value placement:** [are any points, dots, or markers shown? If so, do they fall exactly on a labeled tick mark, on an unlabeled tick mark, or between tick marks?]
**Values visible in image but absent from surrounding text:** [list any numbers or positions that appear only in the image, not in the written task description]
**Complexity level:** [simple / moderate / complex — and one sentence justifying the rating based on the number of elements, precision required, and student demand]

Repeat Part 3A and Part 3B for every activity, including the cool-down.

---

## STEP 4 — ASSESSMENT PROFILE

Using everything extracted above, produce the following summary. This is the structured profile passed directly to the exit ticket writer. Every field must be grounded in what you extracted in Steps 1–3 — do not add anything new here.

---

### STRUCTURED LESSON PROFILE

**Lesson title:**
**Grade:**
**Standards:**

**All learning goals in this lesson (copy exactly from Step 2A — do not paraphrase or reduce):**
[List every learning goal found. Number them. There may be 2, 3, 4, or more — list all of them.]

**Ranked by centrality to this lesson's narrative and activities:**
[Re-order the list above from most central to least central. One sentence per goal explaining why it ranks where it does, grounded in the lesson narrative, activity sequence, or teacher notes.]

**Assessment candidacy — for each goal, note one of the following:**
- Strong MC candidate: the skill or concept can be fairly and fully assessed with a single multiple choice question
- Weak MC candidate: the goal involves a process, construction, or open-ended reasoning that does not reduce well to a single multiple choice question — note why (e.g., "requires student to construct a number line," "requires explaining reasoning," "too broad to assess in one item")

For each goal, also document:
- **Visual necessity rating:** Choose one — `Required` (use when EITHER: (a) the question would be ambiguous or impossible without a visual, OR (b) the construct involves distinguishing between two or more options that are both valid for the same input — in multiple choice format, a student could keyword-match the correct answer from the prompt text without genuinely evaluating the options; a visual showing both applied to the same context is the only way to assess real understanding rather than recall), `Supported` (a visual would strengthen the question but the construct can stand alone in text — use only when every wrong answer choice is obviously inapplicable from the text description alone), or `Text-only` (no visual is needed or useful for this construct)
- **Best visual type for this construct:** Name the specific visual type from the permitted representations list that best serves MC assessment of this construct (e.g., `box_plot_comparative`, `number_line_h`). If the construct is `Text-only`, write "none." This does not commit Prompt 2a to using a visual — it is a recommendation based on what the lesson uses and what would be fair.

[The exit ticket writer will use this field to select 3 constructs. If fewer than 3 goals are strong MC candidates, flag this clearly so the writer knows to work within that constraint.]

**Key vocabulary that must or may appear in exit ticket items:**
[List terms students have seen in this lesson and are expected to use or recognize]

**Permitted number types and value ranges:**
[Be specific — e.g., "integers only, range −10 to 10" or "positive and negative decimals to the tenths place." Ground this in both the text and the image analysis — use the more restrictive of the two if they differ.]

**Permitted representations and contexts:**
[List the specific diagram types, real-world contexts, and representations used in student-facing tasks. Only include representations that appeared in student-facing activities — not teacher-only materials.]

**Difficulty calibration:**
[Describe the difficulty level of the lesson's cool-down or closing problems, including whether values fall on or between tick marks, how much reading or interpretation is required, and how many steps a student must take. Exit ticket items should match this level — not easier, not harder.]

**Language and phrasing patterns to follow:**
[Note specific phrasing the lesson uses that exit ticket items should mirror — e.g., "same distance from 0," "to the left of 0," "the opposite of." Copy phrases exactly from the lesson.]

**Visual conventions and constraints:**
[Synthesized from all image analyses in Step 3B. Specify:]
- Permitted visual types: [list only the types that appeared in student-facing tasks]
- Orientation convention: [horizontal / vertical / both — and which was used in which activity types]
- Scale and range in use: [the actual ranges shown in student-facing images, not just what the text describes]
- Labeled vs. unlabeled tick marks: [what proportion of tick marks were labeled in student-facing tasks — this determines how much interpretation a visual requires]
- Point placement convention: [were points placed on labeled tick marks, unlabeled tick marks, or between tick marks — and at what difficulty level did each appear]
- Complexity ceiling: [the most complex visual used in a student-facing task — exit ticket visuals must not exceed this]
- Values to avoid: [any specific values or configurations that appeared only in teacher-facing materials and should not appear in student-facing exit ticket items]

**Prerequisite prior knowledge assumed by this lesson:**
List every prior skill or concept the lesson explicitly states or clearly implies students should already know before this lesson. Draw from "Building On," narrative phrases, and activity launch instructions. For each item:
- **Skill/concept:** [name it concisely]
- **Source:** [where in the lesson materials it is stated or implied]

If the lesson materials state no prerequisites explicitly, write: "No prerequisites explicitly stated — standard prerequisite skills for this grade band assumed (e.g., arithmetic operations, basic fraction concepts)."

This field is used by Prompts 2c and 2d to evaluate whether any item requires knowledge that is neither taught in this lesson nor a stated prerequisite.

---

**What to EXCLUDE from exit ticket items:**
- Concepts not yet taught:
- Number types not used in this lesson:
- Representations not used in student-facing tasks:
- Vocabulary not introduced in this lesson:
- Visual configurations not used in student-facing tasks:

**Misconception signals from teacher notes:**
Using the instructional notes collected in Step 3A for every activity, produce one numbered entry per misconception signal found. Each entry has four sub-fields:

**Signal [N]:**
- **Source:** activity name and sub-section (e.g., "Activity 2 — Advancing Student Thinking")
- **Error description:** one sentence on exactly what the student does wrong — the specific incorrect action or reasoning, not the abstract concept gap
- **Wrong answer produced:** the specific incorrect value, expression, or graph the student would produce. Copy verbatim from the lesson if named; derive it from the described error if not
- **Priority:** High (lesson names a specific wrong answer explicitly) / Medium (error pattern described but no specific value given) / Low (implied by lesson structure, not explicitly named)

Repeat this block for every signal found. Number them Signal 1, Signal 2, etc.

These signals feed directly into Prompt 2a distractor planning. High-priority signals must appear as planned misconceptions for the relevant construct.

**Cool-down questions (copy exactly):**
[Copy the cool-down questions word for word, including any answer choices, values, and visual descriptions. These are the closest model for exit ticket difficulty, style, and visual complexity.]

---

Output only the STRUCTURED LESSON PROFILE from Step 4. Do not include your working notes from Steps 1–3 in the final output — those are for your internal reasoning only.

---

*Prompt 1 of 5. Output feeds directly into Prompt 2a — Item Planner.*
