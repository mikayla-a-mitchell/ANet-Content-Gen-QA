# Prompt 2a — Define
### Plan 3 exit ticket questions from a structured lesson profile

---

## Inputs provided to you

**Lesson profile input:**

```
{{LESSON_PROFILE}}
```

---

You are an expert math assessment writer for grades 3–8. A structured lesson profile is provided above. Your task is to produce a complete **ITEM PLAN** for 3 multiple choice exit ticket questions aligned to this lesson.

Work through all five steps in order. Show your full reasoning at each step. Do not write any question text, answer choices, or SVG code in this prompt — that happens in Prompt 2b. Your output here is a plan only.

---

## STEP 1 — Select 3 constructs

Using the ranked learning goals from the lesson profile, select exactly 3 constructs to assess — one per question. Follow every rule below.

**Selection rules:**
- Draw only from goals marked as strong MC candidates. Do not force a weak MC candidate into a multiple choice format.
- If the lesson has fewer than 3 strong MC candidates, note this explicitly and select the best available constructs — do not invent constructs not grounded in the lesson.
- If the lesson has more than 3 strong MC candidates, select the 3 ranked highest by centrality to the lesson narrative and note which goals you are setting aside and why.
- Each construct must be directly and fully taught in this lesson — not carried over from a prior lesson, not previewed for a future one.
- Each construct must be distinct from the other two with no skill overlap.
- **If two or more constructs both use the same visual type (e.g., both use comparative box plots), they must test demonstrably different aspects of that visual and use different data values — identical or near-identical visuals with only the question changed is a hard failure.** For lessons that teach two related contrasts (e.g., same median/different IQR versus same IQR/different median), each contrast must get its own distinct data set with different numbers. Document the specific data difference explicitly.
- Each construct must stay within the permitted number types, representations, and vocabulary from the lesson profile.
- **CRITICAL — Do NOT use standards to select or justify constructs.** Standards noted in the lesson profile often cover more content than a single lesson teaches. A standard's full scope is irrelevant here. Constructs must come exclusively from the lesson narrative, learning goals, and learning targets as stated in the lesson profile. If a standard mentions a concept but the lesson narrative and learning goals do not focus on it, that concept is out of scope for this exit ticket — regardless of what the standard says. The lesson profile is the sole source of truth.

**For each construct, document:**
- **Construct:** One sentence naming the specific skill or concept.
- **Source goal:** The exact learning goal or learning target from the lesson profile — copy it verbatim, do not paraphrase.
- **Lesson evidence:** One sentence citing the specific activity or teacher note in the lesson where this construct is explicitly taught.
- **MC candidacy:** One sentence confirming why this construct can be assessed with a single multiple choice question.
- **Scope constraint:** One sentence noting the specific restrictions this construct must honor — permitted number range, representation type, vocabulary, and visual conventions from the lesson profile.
- **Visual necessity:** Copy the visual necessity rating from the lesson profile (`Required` / `Supported` / `Text-only`) and the recommended visual type. These come from Prompt 1's assessment candidacy section — do not re-derive them here.

**Learning goal distribution — required before finalising construct selection:**
If the lesson profile identifies more than one learning goal, the three constructs must collectively represent each goal — not concentrate on one strong goal while leaving others unrepresented. If a learning goal is weak as a full MC candidate, identify its strongest assessable sub-skill and use that. A lesson with three stated goals should produce three items covering one goal each. A lesson with two stated goals should split items across both (e.g., 2+1 or 1+2).

**Hard gate — write the following table before proceeding to Step 2:**
| Item | Construct (one sentence) | Learning goal covered |
|------|--------------------------|----------------------|
| 1    |                          |                      |
| 2    |                          |                      |
| 3    |                          |                      |

If any two rows in the "Learning goal covered" column are identical, the construct selection has failed the diversity requirement — revise before continuing. Do not proceed to Step 2 until each learning goal is represented at least once and no two items share the same learning goal (when the lesson has multiple goals).

**Quality-of-coverage check — required after filling the table:**
Mapping an item to a goal is not enough — verify the item genuinely tests the *full depth* of the goal as the lesson teaches it. Watch for these common surface-level mismatches:

- A goal stated as "interpret [X] in context" is NOT met by an item that mechanically reads a value without context. If the lesson teaches interpretation through real-world scenarios (e.g., temperature, elevation, money), the exit ticket item must include that context. An item asking "What is the value of this point?" tests reading, not interpretation.
- A goal stated as "compare [X] and [Y]" is NOT met by an item that reads one value from a display without comparing it to another.
- A goal stated as "explain why" or "describe the relationship" is NOT met by an item that asks to compute or identify a value without connecting it to meaning.

For each item in the table, write one sentence confirming the item tests the goal at the depth the lesson teaches it — not just the surface label.

**Coverage check — required before finalising construct selection:**
Before locking in the 3 constructs, confirm the set collectively addresses the lesson's primary teaching arc. Most lessons move through a progression — for example: building intuition → core concept → applying or comparing. The 3 constructs should span that arc rather than all clustering at the same phase.

Write one paragraph describing the lesson's teaching arc as you understand it from the lesson profile, then confirm each selected construct maps to a different phase of that arc. If all 3 constructs address the same phase (e.g., all 3 test reading a value off a visual, with no question about interpreting or comparing), flag this and revise the selection before proceeding.



**Visual type distribution check — required before finalising construct selection:**
List the recommended visual type for each of the 3 selected constructs (from the lesson profile's assessment candidacy section). If all 3 are the same visual type, this is a flag — a set of 3 identical visual formats is visually repetitive and suggests the construct selection is too narrow. Revise at least one construct to use a different visual type or no visual, unless the lesson genuinely only uses one visual type throughout all student-facing activities (in which case document this explicitly and proceed).

---

## STEP 2 — Map misconceptions to distractors

For each construct, identify exactly 3 student misconceptions that will drive the 3 distractor answer choices.

**Before selecting misconceptions, read the lesson profile's "Misconception signals from teacher notes" section.** Apply these rules:
- Every **High-priority signal** relevant to this construct must appear as one of the 3 planned misconceptions. Do not replace a High-priority signal with a convenient or easier-to-write distractor.
- **Medium-priority signals** should be used if they fit the construct and no better High-priority signal is available.
- **Derived** misconceptions (not directly named in the lesson profile) are only acceptable when fewer than 3 High/Medium signals exist for the construct.

Each misconception must meet every criterion below.

**Misconception criteria:**
- Plausible for a student who engaged with this specific lesson
- Produces a distinct, predictable wrong answer value
- Reflects a real conceptual or procedural error — not a careless slip
- Sourced from the lesson profile's misconception signals — High-priority signals are binding (see priority rules above); Medium signals are strongly preferred; Derived misconceptions are a last resort only
- **Represents a categorically different type of error from the other two misconceptions for this construct.** Explicitly name the error category for each and confirm all three are different. Categories include but are not limited to: wrong operation, wrong direction, ignoring a component, confusion between two concepts, procedural step skipped, sign error, scale misread, part-whole confusion.
- **Is a likely choice** — a student who holds this misconception would genuinely be drawn to this answer. Reject and replace any distractor that a real student with the stated misconception would not actually choose.

**For each misconception, document:**
- **Error category:** One word or phrase (e.g., "sign error," "wrong operation," "part-whole confusion").
- **Misconception:** One sentence describing the specific reasoning the student follows.
- **Derivation:** Show the step-by-step calculation or reasoning that produces the exact wrong answer value — do not just name the value.
- **Plausibility check:** One sentence explaining why a student who engaged with this lesson would be drawn to this answer.
- **Distractor rationale (draft):** Written in the exact format required — begins "Student [past-tense verb]…", ends with a period, uses general mathematical language with no item-specific numbers or context, no he/she/his/her, no use of the word "failed."

**AC/DR coupling check — required before Step 3:**
For every distractor, verify that following the reasoning in the DR produces the exact value in the AC. If the DR reasoning would produce a different value, revise one or both until they match precisely. Document the result of this check for each distractor explicitly.

**Coincidence check — required before Step 3:**
For any item where the construct requires computing a statistic or value from a visual (IQR, range, median, Q1, Q3, area, perimeter, etc.), verify that the correct answer does not coincidentally equal any other value prominently shown in the figure (e.g., Q1, Q3, min, max, median, or range values). If the correct answer equals a displayed value, the item has a validity flaw — a student can select the right answer for the wrong reason. In this case, adjust the five-number summary or data values in the SCOPE until the correct answer is unique. Document the result: either "PASS — correct answer [X] does not appear elsewhere in the figure" or "REVISED — changed values to ensure correct answer is unique."

**Comparative ambiguity check — required for all comparison items:**
For items asking which group, data set, or entity has greater or lesser variability, spread, or any similar qualitative property: verify the comparison direction is unambiguous given the planned data. The correct answer must lead clearly on ALL measures a student might reasonably apply. For variability items specifically, check both IQR and range — if Group A has the greater range but Group B has the greater IQR (or any reversal), neither group is unambiguously the answer and the item has a fatal flaw. Fix by either: (a) adjusting data values until the correct group leads on all relevant measures, or (b) rewriting the prompt to name the specific statistic being compared (e.g., "using the interquartile range" rather than "has more variability"). Document: "PASS — [group] leads on all relevant measures" or "REVISED — [what changed and why]."

---

## STEP 3 — Plan answer choices

For each question, list all 4 answer choices (correct answer + 3 distractors) and confirm every check below. Write PASS or FLAG for each item. Resolve all flags before moving to Step 4.

- [ ] Choices ordered by default: least to greatest for numeric values; shortest to longest for expressions, equations, statements, or words. This is a default ordering principle, not an absolute rule — logical grouping (e.g., grouping answer choices by the referent, person, or object each one describes) is an acceptable alternative when it better supports student processing. If you deviate from the default ordering, document why.
- [ ] No two choices are equivalent or reducible to the same value
- [ ] The correct answer cannot be reached by a wrong method (no RAWR — correct answer for wrong reason)
- [ ] No distractor is obviously implausible compared to the others
- [ ] For measurement questions: units belong in the prompt as "in [unit]" after the measurement word — not in the answer choices. Exceptions: unit conversion items, money (dollar sign stays in the AC), angle measures in degrees.
- [ ] Distractor values use the exact numbers stated in the problem — no rounded, dropped, or simplified versions. A perimeter distractor for a \\(1\\frac{1}{2} \\times 4\\) rectangle must be \\(2(1\\frac{1}{2} + 4)\\) not \\(2(1 + 4)\\).
- [ ] **Lesson vocabulary only — exclusion list is a hard ban:** Every answer choice must use only vocabulary and representations from the lesson's PERMITTED vocabulary section. **Any term that appears in the lesson profile's 'What to EXCLUDE' section is PROHIBITED as an answer choice** — it is there because it was not taught and must not be assessed. Do not use the exclusion list as a vocabulary source. Example: if 'bar graphs' appears under 'Representations not used in student-facing tasks,' it may not appear as an answer choice regardless of whether students know what a bar graph is.
- [ ] **Word/phrase ordering — character count, not word count:** "Shortest to longest" means total character count including spaces. Count each character explicitly. Example: `Histogram` = 9 chars, `Line graph` = 10 chars, `Circle graph` = 12 chars, `Stem-and-leaf plot` = 18 chars. Sort by this count — not by number of words, not alphabetically.

**Difficulty consistency across the set — required before finalising Step 3:**
The three items must operate at a consistent difficulty level. If one item uses rational numbers, decimals, or mixed numbers while another uses only whole numbers, the set has inconsistent difficulty — a student struggling on the harder item may breeze through the easier one, giving a misleading picture of mastery. Before locking in the answer choice values for all three items: (1) list the complexity tier of the key values used in each item (whole number / non-integer rational / fraction / mixed number), (2) verify all three operate at the same tier or intentionally escalate within the lesson's permitted number types. Flag and revise any item whose values are significantly simpler than the others.

**Same correct answer check — required for all categorical-choice items:**
For items where answer choices are categorical options — graph types, representation names, measure names, properties, strategies — verify that the correct answer differs across those items. Two items with the same correct category (e.g., both answered by "Stem-and-leaf plot," or both answered by "median") test the same fundamental property through different surface prompts — this is a diversity failure. Revise one item so that a different option is correct. Note: for numerical computation items, two items coincidentally producing the same correct value (e.g., both areas equal 12) is acceptable if the constructs are genuinely distinct. Document: "PASS — correct answers are [list]" or "REVISED — [what changed]."

**Consistent-distractor pattern check — required for all 3-item sets:**
A choice value, term, or option that appears as a wrong answer across multiple items while never being correct creates a pattern that test-wise students can identify and exploit — they learn to eliminate it without reasoning about the math. Before finalising: list every distinct choice option across all 3 items and note how many times each appears as a distractor vs. the correct answer. If any option is a distractor in 2 or more items and never the correct answer in any item, flag this and revise at least one item so that option is correct, or remove it from the items where it is weakest. This applies to any type of item — graph type names, measure names, numerical values, expressions, or any other choice format.

---

## STEP 4 — Plan visuals

For each question, decide whether a visual is needed. A visual is needed when the construct cannot be fairly assessed without one — if the construct can be expressed clearly in words alone, do not plan a visual. Use the visual necessity rating from the lesson profile (`Required` / `Supported` / `Text-only`) as the primary guide.

For each question without a visual, write one sentence confirming why no visual is needed.

**CRITICAL — Graph type selection items:** When a question asks students to choose which graph type best represents given data:

1. **Check whether two or more answer choices are both valid for the scenario described** — meaning a student could match the correct answer to a defining phrase in the prompt without actually evaluating the representations. If yes, **NEEDED = yes, no exceptions.** Text alone creates RAWR: the student recognizes a keyword rather than reasoning about the options. A visual showing both plausible options applied to the same context forces genuine evaluation.

   *Example:* in a graph-type lesson, histogram and stem-and-leaf both apply to numerical data — a student can pick the right one by keyword-matching "preserves individual values" without seeing either graph. A side-by-side visual of both removes that shortcut.

2. **Plan the visual** using the registered `panel_comparison` database type (VISUAL_STRATEGY = database). List each plausible option as a panel with its data fields. Do NOT use option_a for this — `panel_comparison` is in the database registry and handles side-by-side graph layouts automatically.

3. **Do NOT rely on the lesson profile's visual necessity rating to override this rule.** A rating of 'Supported' does not mean no visual — it means a visual is optional for some constructs. When two or more choices are mutually plausible, it is not optional.

For each question with a visual, complete the following in order:

---

### STEP 4A — TYPE KEY MATCHING (required first)

Before filling any spec fields, explicitly match the planned visual to the registry. Work through these three steps in writing:

1. **Describe the visual** in one sentence exactly as it appears in the lesson — visual type, orientation, what it shows.
2. **Look up the type key** by comparing the description against the database types list below. State the type key you are assigning and one sentence confirming it matches the lesson description.
3. **Assign the strategy:** If the type key is in the database list → `VISUAL_STRATEGY = database`. If it is in the fallback list → `VISUAL_STRATEGY = option_a` or `option_b` depending on whether values can be constrained to labeled tick marks. If it appears in neither list → `VISUAL_STRATEGY = option_a` and note it in the plan for logging to `unknown_visuals.log`.

Do not proceed to Step 4B until the type key and strategy are confirmed.

---

### STEP 4B — VISUAL SPEC FIELDS

This spec is used by Prompt 2b to produce either a VISUAL_SPEC block (for database renderer types) or SVG code directly (for fallback types). It is also used by Prompt 2b to write distractor rationales — do not proceed to DR writing without completing this spec.

**Database types (use type key confirmed in Step 4A):**
`number_line_h`, `number_line_h_arrow`, `number_line_inequality`, `number_line_v`, `double_number_line`, `fraction_strip`, `tape_diagram`, `area_model_fraction`, `area_model_multiplication`, `array`, `rectangle`, `parallelogram`, `triangle`, `circle`, `right_triangle`, `coordinate_q1`, `coordinate_4q`, `linear_graph`, `slope_triangle`, `bar_graph`, `dot_plot`, `histogram`, `box_plot`, `box_plot_comparative`, `circle_graph`, `scatter_plot`, `two_way_table`, `place_value_chart`, `rectangular_prism_labeled`, `unit_cube_isometric`, `stem_leaf`, `panel_comparison`

> ⚠ **`stem_leaf` and `panel_comparison` are database types — VISUAL_STRATEGY must be `database` for both, never `option_a`.** Do not write custom SVG for registered types.

**Fallback types (not in database — SVG written by Claude in Prompt 2b):**
`composite_figure`, `angle_diagram`, `similar_figures`, `transformation_diagram`, `picture_graph`, `ruler_measurement`, `subtraction_algorithm`, `long_division`, `tree_diagram`, `net_diagram`

If the visual type is not in either list, note this and assign `VISUAL_STRATEGY = option_a` (Claude writes SVG with forced coordinate derivation) or `VISUAL_STRATEGY = option_b` (Claude writes SVG with all values constrained to labeled tick marks).

---

### UNIVERSAL FIELDS — complete for every planned visual

- **Visual type:** Must appear in the lesson profile's permitted visual types. State the type key exactly.
- **VISUAL_STRATEGY:** `database` | `option_a` | `option_b`
- **Necessity justification:** One sentence explaining why this construct cannot be fairly assessed without this visual.
- **Complexity rating:** Simple / moderate / complex — must not exceed the lesson profile's complexity ceiling. Visuals should include only the essential information a student needs to process the construct — nothing decorative or extraneous. One sentence justifying the rating.
- **Color:** Confirm black, white, and gray only — no color.
- **Values and labels shown:** List every number, label, and annotation that will appear. Confirm none are drawn from teacher-facing-only materials.

---

### CONDITIONAL FIELDS — complete only the block matching your visual type

**If VISUAL_STRATEGY = database, add the required data fields for that type:**

*number_line_h / number_line_inequality:*
- axis_min, axis_max, labeled_interval
- points: list of {value, open (bool), label (optional)} — every point must land on a labeled tick mark or precisely calculable half-unit position
- show_arrows (bool), unlabeled_interval (optional)
- **Point label rule:** Only set a label on a point when its value falls at an unlabeled position (i.e., between labeled tick marks). If the point falls exactly on a labeled tick mark, omit the label — the tick mark already displays the value, and a duplicate label is visually distracting. Example: if labeled_interval = 1 and a point is at -4, do not set label: "-4".

*number_line_v (thermometer):*
- axis_min, axis_max, labeled_interval
- points: list of {value} — same constraint as above
- show_bulb (bool), axis_label

*double_number_line:*
- top_min, top_max, top_interval, top_label
- bottom_min, bottom_max, bottom_interval, bottom_label
- tick_values: list of {top, bottom} pairs

*fraction_strip:*
- strips: list of {numerator, denominator, label, shaded_parts (list of 0-based indices)}

*tape_diagram:*
- parts: list of {label, value, shaded (bool)}
- total_label (optional)

*area_model_fraction:*
- total_rows, total_cols, shaded_rows, shaded_cols
- row_label, col_label

*area_model_multiplication:*
- row_parts: list of numbers (e.g., [20, 3])
- col_parts: list of numbers (e.g., [10, 5])
- show_products (bool)

*array:*
- rows, cols

*rectangle:*
- width_value, height_value, unit
- Proportionality check: confirm width_value vs height_value ratio and note which SVG dimension will be larger.

*parallelogram:*
- base_value, height_value, unit

*triangle:*
- base_value, height_value, unit, triangle_type (right/isosceles/scalene)

*circle:*
- radius_value OR diameter_value, unit
- show_radius (bool), show_diameter (bool)

*right_triangle:*
- leg_a_value, leg_b_value, hypotenuse_value (optional), unit

*coordinate_q1:*
- x_max, y_max, x_interval, y_interval, x_label, y_label
- points: list of {x, y, label}

*coordinate_4q:*
- x_min, x_max, y_min, y_max, x_interval, y_interval, x_label, y_label
- points: list of {x, y, label}

*linear_graph:*
- x_min, x_max, y_min, y_max, x_interval, y_interval, x_label, y_label
- lines: list of {x1, y1, x2, y2, label, dashed (bool)}

*slope_triangle:*
- Same as linear_graph plus:
- slope_triangle: {x_start, x_end, y_start, y_end, run_label, rise_label}

*bar_graph:*
- categories: list of strings
- values: list of numbers
- y_min, y_max, y_interval, x_label, y_label

*dot_plot:*
- axis_min, axis_max, labeled_interval
- dots: list of values (duplicates stack)
- x_label

*histogram:*
- bins: list of {min, max, frequency}
- y_max, y_interval, x_label, y_label

*box_plot:*
- axis_min, axis_max, labeled_interval, axis_label
- min, q1, median, q3, max — ALL values must land exactly on labeled tick marks
- **Tick alignment check — REQUIRED:** Confirm that min, Q1, median, Q3, and max all land exactly on labeled tick marks given the axis_min, axis_max, and labeled_interval chosen. If any value falls between labeled ticks, adjust the data values until they do. State the adjustment explicitly.

*box_plot_comparative:*
- Same as box_plot plus:
- groups: list of {label, min, q1, median, q3, max} — Group A listed first (renders at top)
- Complete the data verification table for EACH group

*circle_graph:*
- slices: list of {label, percentage} — must sum to 100

*stem_leaf:*
- stems: list of {value, leaves}  — value is the stem digit, leaves is a space-separated string of leaf digits
- title (optional)
- key (optional, e.g. "7|4 means 74")

*panel_comparison:*
- panel_count: 2 or 3  (max 3 — 4 panels are too small to read on a student document)

> **CRITICAL — Answer choices for panel_comparison items must match displayed panels:** Every answer choice must name a graph type that is actually displayed in one of the panels. Answer choices that name graph types not shown in any panel are a hard failure — students can eliminate them by inspection without mathematical reasoning, which is a form of RAWR. Before finalising the AC list: (1) list every graph type shown across all panels, (2) verify every AC maps to one of those types. If the AC list requires more distinct graph types than the panels contain, either add panels or reduce the number of distinct AC types to match what is shown.
- panels: list of panel dicts, each containing type, title (optional), and compact data fields:
  - **histogram panel**: axis_min, axis_max, y_max, y_interval, axis_label, bin_counts (space-separated integer counts, one per bin)
  - **stem_leaf panel**: rows ("5:4 6:7 7:2,4,6,8" — stem:comma-sep-leaves tokens, space-separated), key
  - **circle_graph panel**: slices ("label1:pct1 label2:pct2" — space-separated label:percentage tokens)
  - **Other panel types**: pass fields through directly using the type's standard spec keys

Example for a histogram + stem-and-leaf comparison:
```
panel_count: 2
panel_0_type: histogram
panel_0_title: Graph A: Histogram
panel_0_axis_min: 50
panel_0_axis_max: 100
panel_0_y_max: 5
panel_0_y_interval: 1
panel_0_axis_label: Score
panel_0_bin_counts: 1 1 4 3 2
panel_1_type: stem_leaf
panel_1_title: Graph B: Stem-and-Leaf Plot
panel_1_key: 7|4 means 74
panel_1_rows: 5:4 6:7 7:2,4,6,8 8:0,2,4,5,6,7,9 9:0,1,2,3,5
```

*scatter_plot:*
- x_min, x_max, x_interval, x_label
- y_min, y_max, y_interval, y_label
- points: list of {x, y}
- trend_line: {x1, y1, x2, y2} (optional)

*two_way_table:*
- row_header, col_header
- row_labels: list of strings
- col_labels: list of strings
- values: list of lists (rows × cols)
- show_totals (bool)

*place_value_chart:*
- columns: list of strings (e.g., ["Thousands", "Hundreds", "Tens", "Ones"])
- values: list of integers

*rectangular_prism_labeled:*
- length_value, width_value, height_value, unit

*unit_cube_isometric:*
- cubes: list of [x, y, z] positions
- cube_size (optional, default 40)
- depth_dx, depth_dy (optional, default 14)

**If VISUAL_STRATEGY = option_a or option_b:**
- Describe the visual in enough detail that Prompt 2b can write the SVG: what elements appear, what data values are shown, what labels are used, and the approximate layout (e.g., side-by-side panels, single figure).
- For option_b: confirm all displayed values fall on labeled tick marks.
- **Do NOT compute pixel coordinates or derivation tables here.** Prompt 2b will derive all coordinates when writing the SVG. Pixel math in the item plan adds length without benefit — describe intent, not implementation.
- **Write this description with enough precision to double as a real illustration request.** If this visual is ever handed off to a human illustrator instead of (or in addition to) Prompt 2b, ANet's actual process for that handoff is emailing the item ID, a sketch or reference image, and detailed include/exclude notes, with a 2–4 day turnaround — so a precise, unambiguous description here carries real value beyond just feeding Prompt 2b.

---

### VISUAL DISTINCTNESS — if more than one question uses the same visual type

If two questions both use the same visual type (e.g., both are `box_plot_comparative`), confirm all three before proceeding to CROSS-VISUAL CONSISTENCY:

1. **Different data values:** List the key data values for each visual side by side and confirm they are numerically different. Two comparative box plots with the same five-number summaries is a hard failure.
2. **Group labels must match stem language:** If the item stem describes groups generically ("two groups," "two teams," "two classes"), the visual labels must be equally generic ("Group A" / "Group B", "Team A" / "Team B"). Do not substitute lesson context names (mascots, team names) when the stem does not use them — this creates a mismatch between what the student reads and what the visual shows. Only use specific names when the stem itself names the groups. Do not reuse the same generic labels across two visuals in the same exit ticket.
3. **Different constructs tested:** Confirm the question asked about each visual targets a different concept. Two box plot questions asking about different properties (median vs IQR) with different data are acceptable; the same question reworded with the same data is not.

---

### CROSS-VISUAL CONSISTENCY — if more than one question has a visual

All visuals in the exit ticket must use the same layout conventions. Before finalising Step 4, confirm:
- Same gap between data elements and axis line across all data displays
- Same label positioning convention
- Same axis label placement

---

## STEP 5 — Bias and sensitivity review

For each planned question, check every item below. Write PASS or FLAG with one sentence. Resolve all flags before outputting the ITEM PLAN.

- [ ] No question creates an advantage or disadvantage for any subgroup
- [ ] No polysemous words that could confuse the construct being assessed
- [ ] No prior-grade content included that is not a direct prerequisite to the construct
- [ ] No unnecessary context that adds linguistic demand without adding mathematical clarity
- [ ] **No sensitive or stereotype-adjacent contexts.** Data involving racial, ethnic, religious, political, or socioeconomic group membership is sensitive and must be avoided regardless of whether the data is factual or from a reputable source. Do not use percentage breakdowns, ratios, or counts by race, ethnicity, religion, national origin, immigration status, or income level. Replace with neutral demographic categories (age groups, geographic regions, school grade levels, academic subjects) or non-demographic contexts entirely.
- [ ] No gendered pronouns (he/she/his/her) — only they/their
- [ ] "Mrs." not used — only "Ms." if any title appears
- [ ] No gender binary context implied
- [ ] Difficulty matches the lesson's cool-down level — not easier, not harder

---

## OUTPUT FORMAT

After completing all five steps, output the ITEM PLAN in the exact tagged structure below. This is machine-parsed by Prompt 2b — do not add commentary before or after the block.

```
<ITEM_PLAN>

<LESSON>
<TITLE>[Lesson title]</TITLE>
<GRADE>[Grade]</GRADE>
<STANDARDS>[Standard codes, comma separated]</STANDARDS>
</LESSON>

<ITEM id="1">
<CONSTRUCT>[One sentence]</CONSTRUCT>
<SOURCE_GOAL>[Exact verbatim learning goal from lesson profile]</SOURCE_GOAL>
<LESSON_EVIDENCE>[One sentence citing activity or teacher note]</LESSON_EVIDENCE>
<SCOPE>[Number range, representation, vocabulary constraints]</SCOPE>

<MISCONCEPTIONS>
<MISCONCEPTION id="a">
  <SOURCE>[Lesson profile signal this misconception is drawn from — copy the signal priority (High/Medium/Low) and the source sub-section (e.g., "High — Activity 2 Advancing Student Thinking"). Write "Derived" if not directly named in the lesson profile.]</SOURCE>
  <ERROR_CATEGORY>[category]</ERROR_CATEGORY>
  <REASONING>[student's flawed reasoning]</REASONING>
  <WRONG_ANSWER>[exact value, with derivation]</WRONG_ANSWER>
  <DR>[Distractor rationale — plain text, begins Student…, ends with period]</DR>
  <ACDR_CHECK>[PASS or FAIL with one sentence]</ACDR_CHECK>
</MISCONCEPTION>
<MISCONCEPTION id="b">...</MISCONCEPTION>
<MISCONCEPTION id="c">...</MISCONCEPTION>
</MISCONCEPTIONS>

<ANSWER_CHOICES>
<CHOICE label="A">[value]</CHOICE>
<CHOICE label="B">[value]</CHOICE>
<CHOICE label="C">[value]</CHOICE>
<CHOICE label="D">[value]</CHOICE>
<CORRECT>[Letter of correct answer]</CORRECT>
</ANSWER_CHOICES>

<VISUAL_PLAN>
<NEEDED>[yes | no]</NEEDED>
<TYPE>[type key or none]</TYPE>
<STRATEGY>[database | option_a | option_b | none]</STRATEGY>
<SPEC>
[All data fields for the visual type, as documented in Step 4]
[For database types: structured key-value pairs]
[For fallback types: full description of what to show — layout, data values, labels. No pixel coordinates.]
</SPEC>
</VISUAL_PLAN>

<COINCIDENCE_CHECK>[PASS — correct answer does not equal any value displayed in the figure | REVISED — describe what was changed and why | N/A — no computed value derived from a visual]</COINCIDENCE_CHECK>
<BIAS_REVIEW>[PASS or list of resolved flags]</BIAS_REVIEW>

</ITEM>

<ITEM id="2">
...
</ITEM>

<ITEM id="3">
...
</ITEM>

</ITEM_PLAN>
```

---

*Item planning stage of the anet-exit-ticket-studio pipeline (extraction → item planning → item creation → content review → bias review → render). Input: structured lesson profile. Output: ITEM PLAN feeds into item creation.*
