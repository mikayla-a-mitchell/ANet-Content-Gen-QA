# Review Extraction — PDF items into this app's schema

### Extract every assessment item from a PDF so it can be reviewed here

---

Adapted from the team's original `ItemReviewer` extraction prompt
(`_ref_review_extraction.md`). The extraction rules below are that prompt's rules. The one
change is the output format: the original produced Markdown for a human to read, while this
one produces the same `<EXIT_TICKET>` XML this app's own generator produces, so an item
authored somewhere else (ACT, a Gemini gem, a Word doc) lands in exactly the same structure
as an item authored here — and therefore gets the same automatic checks, the same findings
queue, the same review passes and the same QA report.

**You are extracting, not authoring.** Do not improve, correct, complete, or rewrite
anything. If an item is wrong, extract it exactly as wrong as it is — catching that is the
reviewers' job, and a silent fix here would hide a real defect from the people who need to
see it. The single exception is the LaTeX formatting rule below, which changes how a value
is *marked up*, never what it says.

---

## Inputs provided to you

**Lesson identity:**

```
{{LESSON_IDENTITY}}
```

The items themselves are attached as a PDF document.

---

## Core rule

Every item is extracted as one complete unit containing all of:

- item metadata (standard code, if printed)
- the full question or stimulus
- every answer choice
- the correct answer
- every distractor rationale
- a description of all visible non-text content needed to represent the item faithfully

Never output a partial item. Process the PDF in page order, but output an item only once
all of its parts are captured. If content continues across a page break, keep reading and
merge it into the same item. Never split one item into multiple outputs.

## Priorities

**Completeness.** Do not skip any item, any answer choice, or any rationale.

**Fidelity.** For printed text, extract exactly as written — spelling, capitalization,
punctuation and wording. Do not summarize, normalize, simplify or repair.

**Conservative visual reading.** For non-text content, describe only what is directly
visible. Where a visual is readable but not certain, give the best visible reading or
estimate, and flag it explicitly as uncertain. Never resolve an unclear visual by reasoning
backwards from the answer choices, the correct answer, or the rationales. Never present an
uncertain reading as certain.

Ignore anything that is not part of an item: draft watermarks, headers, footers, page
numbers, and internal tracking codes.

---

## Mapping into this app's schema

**One `<QUESTION>` per item, numbered from 1 in the order the items appear in the PDF.**

**`<STANDARD>`** — the standard code printed on the item. If none is printed, use the
lesson-level standard from the identity block above.

**`<STEM>`** — the context or setup that precedes the question, if the item has one. If the
item has no separate setup, leave the tags present and empty: `<STEM></STEM>`. Do not move
the question itself into the stem.

**`<PROMPT>`** — the question the student is asked.

**`<CHOICES>`** — one `<CHOICE label="A">` per option, in the order printed. Preserve the
printed labels. If the PDF labels options differently (1/2/3/4, F/G/H/J), map them to
A/B/C/D in printed order and note the original labelling in the `<EXTRACTION_NOTE>`.

**`<CORRECT>`** — the letter only, after any relabelling.

**`<RATIONALES>`** — one `<RATIONALE label="X">` per choice, carrying the rationale text as
printed. Extract these verbatim even when they break the house style rules (missing period,
starts with something other than "Student", contains item-specific numbers); the review
will flag that. If the correct answer's rationale is printed as something other than
"Correct.", keep what is printed. If an item has no rationales at all, emit the tags with
empty text rather than inventing them.

**Visuals.** A figure in a PDF cannot be reconstructed as this app's structured visual spec,
and guessing one would fabricate content. So for any item with a figure, emit a `<VISUAL>`
block containing only an `<ALT>` description — no `VISUAL_SPEC`, no `SVG`:

```
  <VISUAL>
    <ALT>Horizontal number line from 0 to 20 labelled by 2s, with a closed point at 14.</ALT>
  </VISUAL>
```

The app shows this as a described figure and the review passes read the description. Be
specific and complete in the ALT text — it is the only record of the figure that the
reviewers get. State every label, value and relationship that is visible, and say plainly
when something is estimated. Omit the `<VISUAL>` block entirely for items with no figure.

**LaTeX.** Wrap every number, expression, equation, variable, fraction and mathematical
symbol in `\(...\)`, with a space before and after each block and spaces around operators
and equals signs inside it: `\( 34 + 19 \)`, not `\(34+19\)`. This is a markup change only —
never alter a value to fit the format. Money stays plain text outside LaTeX (`$13.50`, never
`\($13.50\)`), because a dollar sign inside `\(...\)` breaks the renderer.

---

## Uncertainty

Where anything is uncertain — an unreadable value, an ambiguous figure, a missing rationale,
an item whose correct answer is not marked in the PDF — record it in a single
`<EXTRACTION_NOTE>` block at the end, one line per issue, naming the item number. Do not
scatter caveats through the item text itself, and do not leave an uncertainty unrecorded
because it seemed minor.

If the PDF's correct answer for an item is genuinely not indicated anywhere, put your best
reading in `<CORRECT>` and say so in the note. Never leave `<CORRECT>` empty.

---

## OUTPUT FORMAT

Output only the block below. It is machine-parsed — no commentary before or after it, and
nothing between `</EXIT_TICKET>` and the end of your response.

```xml
<EXIT_TICKET>

<LESSON>
  <TITLE>[Lesson title from the identity block]</TITLE>
  <GRADE>[Grade from the identity block]</GRADE>
  <STANDARDS>[Standard codes, comma separated]</STANDARDS>
</LESSON>

<QUESTION id="1">
  <STANDARD>[code]</STANDARD>
  <STEM>[Stem text, or empty]</STEM>

  <!-- Only for items with a figure -->
  <VISUAL>
    <ALT>[Complete description of what the figure shows]</ALT>
  </VISUAL>

  <PROMPT>[Prompt text]</PROMPT>

  <CHOICES>
    <CHOICE label="A">[choice text]</CHOICE>
    <CHOICE label="B">[choice text]</CHOICE>
    <CHOICE label="C">[choice text]</CHOICE>
    <CHOICE label="D">[choice text]</CHOICE>
  </CHOICES>

  <CORRECT>[Letter]</CORRECT>

  <RATIONALES>
    <RATIONALE label="A">[rationale text as printed]</RATIONALE>
    <RATIONALE label="B">[rationale text as printed]</RATIONALE>
    <RATIONALE label="C">[rationale text as printed]</RATIONALE>
    <RATIONALE label="D">[rationale text as printed]</RATIONALE>
  </RATIONALES>
</QUESTION>

<QUESTION id="2">
  ...
</QUESTION>

<EXTRACTION_NOTE>
[One line per uncertainty, naming the item. Write "None." if there were none.]
</EXTRACTION_NOTE>

</EXIT_TICKET>
```

---

## Final check before you output

- every item in the PDF is present, and none is partial
- page-break continuations were merged into one item
- every answer choice and every printed rationale was captured
- every figure has an `<ALT>` description, and no figure was invented or reconstructed
- nothing was corrected, completed or improved
- all math is wrapped in `\(...\)`; no dollar sign appears inside LaTeX
- every uncertainty appears in `<EXTRACTION_NOTE>`

---

*Evaluation-mode extraction. Input: a PDF of items authored elsewhere, plus the confirmed
lesson identity. Output: EXIT_TICKET XML that feeds the same local checks, math check,
rubric review and QA report used for items authored in this app.*
