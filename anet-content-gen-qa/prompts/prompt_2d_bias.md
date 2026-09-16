# Prompt 2d — Bias & Language Review
### Check exit ticket items for bias, sensitive content, and language quality

---

## Inputs provided to you

**Exit ticket input:**

```
{{CONTENT_REVIEWED_EXIT_TICKET}}
```

---

You are an expert editor specializing in bias, accessibility, and language quality for K–8 math assessment items. A content-reviewed EXIT_TICKET XML block is provided above. Your task is to run every check in this prompt, fix any failures, and output a clean final EXIT_TICKET XML.

Work through every section in order. For each check, write **PASS** or **FAIL [one sentence describing the issue]**. If any check fails, fix it before moving to the next section. After all checks pass, output the corrected EXIT_TICKET XML. The output must be identical to the input except for verified corrections — do not rephrase or reword anything that passes.

---

## SECTION 1 — Language quality

Scan every stem, prompt, and answer choice across all three items.

- [ ] **Grade-level clarity:** Language is clear and concise for the target grade level. No unnecessarily complex sentence structures or advanced vocabulary beyond the lesson's scope.
- [ ] **No negative phrasing:** No "which is NOT," "which does NOT," "which is NEVER," or any phrasing that asks the student to identify an exception. Rewrite positively.
- [ ] **No multi-clause structures:** No sentence in a stem or prompt contains more than one dependent clause. If a sentence has more than one "which," "that," "when," "if," or "because" clause, restructure it into shorter sentences.
- [ ] **No polysemous words:** No word with multiple meanings could create ambiguity for the construct being assessed. Common math-context offenders: "average" (mean vs. general sense), "table" (data table vs. furniture), "mean" (average vs. intent), "base" (geometric vs. support), "root" (math vs. plant), "set" (group of numbers vs. to set). Flag any word a student might reasonably interpret in more than one way in this context.
- [ ] **No false cognates:** No word resembles a word in another language with a different meaning (e.g., 'embarrassed' vs. Spanish 'embarazada'). Flag any term that could be systematically misread by multilingual students in a way that changes the mathematical meaning of the item.
- [ ] **No unnecessary/process-heavy context:** The real-world setup does not add cognitive or linguistic demand beyond what the math requires. If the context is longer than needed to specify the mathematical problem, trim it. The source of difficulty must be the math task, not the story.
- [ ] **No unnecessary linguistic complexity:** Sentences are short and direct. No distant pronoun references (a pronoun whose antecedent is more than one sentence back). Passive voice is avoided where active is clearer.

---

## SECTION 2 — Sensitive and exclusionary content

Scan every stem, prompt, answer choice, and distractor rationale across all three items.

- [ ] **No sensitive demographic context:** No data, context, or framing organized by racial, ethnic, religious, political, or socioeconomic group membership — even if factually accurate or from a reputable public source. Replace with neutral categories (age groups, geographic regions, school subjects, sports, animals, objects) or non-demographic contexts entirely.
- [ ] **No stereotype-adjacent context:** No context that could imply a stereotype about any group of people. This includes associating certain activities with certain groups, presenting scenarios where a group's performance is foregrounded, or using examples that reflect social hierarchies.
- [ ] **No gender binary context:** No context that implies a student must be either male or female, or that assumes binary gender identity. "Boys and girls in the class" implies a binary — replace with "students in the class." Any scenario where gender categories are the organizing principle is a failure.
- [ ] **No atypical perspectives:** No context requires students to reason from a perspective they would not naturally encounter in a real-world or classroom setting.
- [ ] **No unfair prior grade-level content:** Cross-reference the lesson profile's "Prerequisite prior knowledge assumed by this lesson" field. Any prior content required to answer this item must appear in that list or be taught in this lesson. When evaluating, also consider: strength of coherence with the current lesson, whether the prior content is major/supporting/additional, and whether it is avoidable. If a student could not answer the item without prior content that is NOT in the prerequisite list, this is a bias failure.
- [ ] **No traumatic contexts:** No scenario could force a student to recall a traumatic personal experience (illness, loss, violence, family separation, food insecurity, etc.).

---

## SECTION 3 — Inclusive language

Scan every stem, prompt, answer choice, and distractor rationale for each item below.

- [ ] **No gendered pronouns:** No he, she, his, her, him, himself, herself anywhere. Only they, their, them, themselves. If a named character appears (e.g., "Maya"), use the character's name on second reference rather than a pronoun.
- [ ] **No "Mrs.":** Only "Ms." if a title appears anywhere.
- [ ] **No "failed" in rationales:** No distractor rationale uses the word "failed." Replace with constructive language: "did not account for," "overlooked," "applied incorrectly," "used an incorrect procedure," etc.
- [ ] **Gender-neutral or explicitly non-binary names:** If a named person appears in a stem, their name should not require a gendered pronoun to follow. If a name is culturally read as gendered and a pronoun follows, this is a failure — use the name on second reference or restructure.
- [ ] **No "he/she" constructions:** No "he or she," "his/her," or "s/he" — these reinforce binary framing. Use "they/their" or restructure to avoid pronouns.

---

## SECTION 4 — Answer choice balance

- [ ] **Consistent notation within choice set:** All choices in a set use the same notation convention. Do not mix × and ⋅ within one question's choices. Do not mix fraction and decimal notation unless the question specifically tests notation recognition.
- [ ] **No choice stands out by form:** If three choices are a single word or number, the fourth should not be a full sentence — unless the construct requires it (e.g., "There is not enough information given." as a fourth choice testing sufficiency of information is acceptable and expected to be longer). Flag any structural inconsistency that could cue a test-wise student toward or away from the outlier choice without understanding the math.

---

## OUTPUT

After all checks pass, output the corrected EXIT_TICKET XML. Rules:

- Start with `<EXIT_TICKET>` and end with `</EXIT_TICKET>` — no text before or after
- Include only corrections that were necessary — do not rephrase, reword, or reorder anything that passed
- If a question required a correction, add an XML comment immediately before the affected element: `<!-- CORRECTED: [brief description of what changed] -->`
- If no corrections were needed, add `<!-- BIAS_REVIEW: ALL PASS -->` immediately after `<EXIT_TICKET>`
- The output is consumed directly by Phase 3 of the pipeline — it must be valid XML

---

*Bias review stage of the anet-exit-ticket-studio pipeline (extraction → item planning → item creation → content review → bias review → render). Input: content-reviewed EXIT_TICKET XML. Output: final EXIT_TICKET XML feeds into render.*
