"""
Local item validation — instant, free, no API calls.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mechanical checks over a parsed exit ticket. Every check that can be decided
by arithmetic or by a formatting rule lives here rather than in a model call,
because those are exactly the defects a human reviewer misses most reliably
and a model costs money to re-derive.

Output is a list of FINDING records, the same shape the Phase 2 review's
model findings use, so both land in one queue in the app:

    {
      "id":       stable hash — survives re-runs so decisions stick
      "item":     question id, e.g. "2"
      "source":   "local"
      "check":    human-readable check name
      "severity": "high" | "medium" | "low"
      "field":    dotted path the fix would touch, e.g. "rationale.C"
                  (None when the finding isn't a single-field fix)
      "current":  current value of that field
      "proposed": suggested replacement, or None when no automatic fix exists
      "reason":   one sentence on why this is a problem
    }

A finding with a `proposed` value can be applied with one click. A finding
without one is a flag for a human to resolve.

Severity is about consequence, not effort:
  high   — the item is wrong or unfairly answerable (a student could score
           without understanding, or the key is unreachable)
  medium — a real quality defect a reviewer would send back
  low    — house-style and formatting
"""

from __future__ import annotations

import ast
import hashlib
import re
import shutil
import subprocess
from typing import Optional

SEV_HIGH = "high"
SEV_MED = "medium"
SEV_LOW = "low"

# Commands this pipeline's items legitimately use. Anything outside this set
# is flagged for a human to confirm rather than silently shipped — see the
# fallback in check_latex() for why.
KNOWN_LATEX_COMMANDS = {
    "frac", "dfrac", "tfrac", "underline", "overline", "phantom", "hphantom",
    "hspace", "quad", "qquad", "square", "times", "cdot", "div", "pm",
    "neq", "ne", "le", "leq", "ge", "geq", "lt", "gt", "approx",
    "left", "right", "text", "textbf", "mathbf", "sqrt", "angle", "circ",
    "degree", "pi", "percent", "dots", "ldots", "cdots", "rule", "mathrm",
}


# ── helpers ───────────────────────────────────────────────────────────────────
def _finding(item: str, check: str, severity: str, reason: str,
             field: Optional[str] = None, current: Optional[str] = None,
             proposed: Optional[str] = None) -> dict:
    basis = f"{item}|{check}|{field or ''}|{current or ''}"
    return {
        "id": hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12],
        "item": item,
        "source": "local",
        "check": check,
        "severity": severity,
        "field": field,
        "current": current,
        "proposed": proposed,
        "reason": reason,
    }


def strip_latex(s: str) -> str:
    """Plain-text form of a field: unwrap \\(...\\) and drop LaTeX commands
    so the text can be parsed arithmetically or counted for length."""
    if not s:
        return ""
    out = re.sub(r"\\[()]", "", s)
    out = out.replace(r"\times", "*").replace(r"\cdot", "*").replace(r"\div", "/")
    out = out.replace(r"\neq", "!=").replace(r"\le", "<=").replace(r"\ge", ">=")
    out = re.sub(r"\\underline\{[^}]*\}", "___", out)
    out = re.sub(r"\\phantom\{[^}]*\}", "", out)
    out = re.sub(r"\\[a-zA-Z]+", " ", out)
    out = out.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", out).strip()


_ALLOWED_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                  ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd)


def safe_eval(expr: str) -> Optional[float]:
    """Evaluate a simple arithmetic expression, or None if it isn't one.
    Deliberately restricted to number literals and + - * / so nothing from
    an item's text can execute."""
    expr = expr.strip()
    if not expr or not re.fullmatch(r"[0-9\s\+\-\*/\.\(\)]+", expr):
        return None
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return None
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            return None
    try:
        return float(eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {}))
    except Exception:
        return None


def choice_value(text: str) -> Optional[float]:
    """Numeric value of a choice, when it is a value or an expression.
    Returns None for equations (containing '=') and for anything unparseable."""
    plain = strip_latex(text)
    if "=" in plain or "!=" in plain:
        return None
    return safe_eval(plain)


def equation_sides(text: str) -> Optional[tuple]:
    """(left, right) values for a choice that is an equation, else None."""
    plain = strip_latex(text)
    if plain.count("=") != 1 or "!=" in plain:
        return None
    left, right = plain.split("=")
    lv, rv = safe_eval(left), safe_eval(right)
    if lv is None or rv is None:
        return None
    return lv, rv


def _numbers_in(text: str) -> list:
    return [float(n) for n in re.findall(r"\d+(?:\.\d+)?", strip_latex(text))]


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


# ── LaTeX validity (uses node+katex when present, patterns otherwise) ─────────
_KATEX_AVAILABLE: Optional[bool] = None


def katex_available() -> bool:
    global _KATEX_AVAILABLE
    if _KATEX_AVAILABLE is None:
        if not shutil.which("node"):
            _KATEX_AVAILABLE = False
        else:
            try:
                r = subprocess.run(
                    ["node", "-e", "require('katex');console.log('ok')"],
                    capture_output=True, text=True, timeout=15,
                )
                _KATEX_AVAILABLE = r.returncode == 0
            except Exception:
                _KATEX_AVAILABLE = False
    return _KATEX_AVAILABLE


def katex_errors(snippets: list) -> dict:
    """{snippet: error message} for snippets KaTeX refuses. Empty when KaTeX
    isn't installed — the pattern checks below still run in that case."""
    if not snippets or not katex_available():
        return {}
    script = (
        "const katex=require('katex');"
        "const xs=JSON.parse(process.argv[1]);const out={};"
        "for(const x of xs){try{katex.renderToString(x,{throwOnError:true});}"
        "catch(e){out[x]=e.message;}}"
        "console.log(JSON.stringify(out));"
    )
    try:
        import json as _json
        r = subprocess.run(["node", "-e", script, _json.dumps(snippets)],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return _json.loads(r.stdout or "{}")
    except Exception:
        pass
    return {}


# ── individual checks ─────────────────────────────────────────────────────────
def check_structure(q: dict) -> list:
    out = []
    item = q["id"]
    choices = q.get("choices", [])
    rationales = q.get("rationales", [])
    labels = [c["label"] for c in choices]

    if len(choices) != 4:
        out.append(_finding(item, "Four answer choices", SEV_HIGH,
                            f"This item has {len(choices)} answer choices; every item needs exactly 4."))
    if len(rationales) != len(choices):
        out.append(_finding(item, "One rationale per choice", SEV_HIGH,
                            f"{len(choices)} choices but {len(rationales)} rationales."))
    correct = (q.get("correct") or "").strip()
    if correct not in labels:
        out.append(_finding(item, "Correct answer is a real choice", SEV_HIGH,
                            f"CORRECT is {correct!r}, which is not one of {labels}."))
    return out


def check_rationales(q: dict) -> list:
    out = []
    item = q["id"]
    correct = (q.get("correct") or "").strip()

    # A rationale reading exactly "Correct." identifies itself as the correct
    # answer's rationale. Trusting only <CORRECT> meant that when generation
    # left that tag empty or mismatched, this function treated "Correct." as a
    # distractor rationale and complained it did not begin with "Student" —
    # a confusing false accusation on the one rationale that was right.
    self_declared = {r["label"] for r in q.get("rationales", [])
                     if (r.get("text") or "").strip() == "Correct."}
    labels = {c["label"] for c in q.get("choices", [])}
    if correct not in labels and len(self_declared) == 1:
        correct = next(iter(self_declared))

    for r in q.get("rationales", []):
        lbl, text = r["label"], (r.get("text") or "").strip()
        field = f"rationale.{lbl}"

        if lbl == correct or lbl in self_declared:
            if text != "Correct.":
                out.append(_finding(item, "Correct-answer rationale", SEV_LOW,
                                    "The correct answer's rationale must be exactly 'Correct.'",
                                    field, text, "Correct."))
            continue

        if not text:
            out.append(_finding(item, "Rationale present", SEV_HIGH,
                                "This distractor has no rationale.", field, text))
            continue
        if not text.startswith("Student "):
            out.append(_finding(item, "Rationale opens with 'Student'", SEV_LOW,
                                "Distractor rationales begin with 'Student' followed by a past-tense verb.",
                                field, text))
        if not text.endswith("."):
            out.append(_finding(item, "Rationale ends with a period", SEV_LOW,
                                "Distractor rationales end with a period.",
                                field, text, text.rstrip() + "."))
        if re.search(r"\\\(|\\\)|\\frac|\$", text):
            out.append(_finding(item, "No LaTeX in rationales", SEV_MED,
                                "Rationales are plain text; LaTeX renders as literal markup here.",
                                field, text))
        if "failed" in text.lower():
            out.append(_finding(item, "No 'failed' in rationales", SEV_LOW,
                                "House style avoids 'failed'; describe what the student did instead.",
                                field, text))
        gendered = re.findall(r"\b(he|she|his|her|him|himself|herself)\b", text, re.I)
        if gendered:
            out.append(_finding(item, "No gendered pronouns", SEV_MED,
                                f"Uses {', '.join(sorted(set(w.lower() for w in gendered)))}; use they/their.",
                                field, text))
        if re.search(r"\bMrs\.", text):
            out.append(_finding(item, "No 'Mrs.'", SEV_LOW,
                                "House style uses 'Ms.' only.", field, text))
        if re.search(r"\bstudent\b", text[len("Student "):], re.I):
            out.append(_finding(item, "'Student' used once", SEV_LOW,
                                "After the opening 'Student', make the mathematical object the subject "
                                "rather than naming the student again.", field, text))
        if text.count(".") > 1 and " OR " not in text and ";" not in text:
            out.append(_finding(item, "Rationale is one sentence", SEV_LOW,
                                "Rationales are one sentence unless two error paths reach the same answer.",
                                field, text))
    return out


def check_latex(q: dict) -> list:
    out = []
    item = q["id"]
    fields = [("stem", q.get("stem", "")), ("prompt", q.get("prompt", ""))]
    fields += [(f"choice.{c['label']}", c.get("text", "")) for c in q.get("choices", [])]

    snippets, owner = [], {}
    for field, text in fields:
        if not text:
            continue
        if re.search(r"\\\(\s*\$|\$\s*\\\)", text) or re.search(r"\\\([^)]*\$", text):
            out.append(_finding(item, "No money inside LaTeX", SEV_HIGH,
                                "A dollar sign inside \\(...\\) breaks KaTeX; write money as plain text.",
                                field, text))
        if "$" in text and not re.search(r"\\\(", text):
            pass  # plain-text money is correct
        if text.count(r"\(") != text.count(r"\)"):
            out.append(_finding(item, "Balanced LaTeX delimiters", SEV_HIGH,
                                "Unbalanced \\( and \\) — this renders as literal markup.", field, text))
        for m in re.finditer(r"\\\((.+?)\\\)", text, re.DOTALL):
            body = m.group(1)
            snippets.append(body)
            owner.setdefault(body, (field, text))
            if re.search(r"\d[\+\-=]|[\+\-=]\d", body.replace(" ", "\u0000").replace("\u0000", " ")):
                pass
            tight = re.search(r"[0-9)]\s*(?:[\+\-]|=)\s*[0-9(]", body)
            if tight and not re.search(r"[0-9)] (?:[\+\-]|=) [0-9(]", body):
                spaced = re.sub(r"\s*([\+\-=])\s*", r" \1 ", body)
                spaced = re.sub(r"\s+", " ", spaced).strip()
                out.append(_finding(item, "Spaces around operators in LaTeX", SEV_LOW,
                                    "House style puts a space on both sides of +, - and = inside LaTeX.",
                                    field, text, text.replace(body, f" {spaced} ")))
        for m in re.finditer(r"(\S)\\\(", text):
            out.append(_finding(item, "Space before LaTeX", SEV_LOW,
                                "Every \\(...\\) block needs a space before it in surrounding text.",
                                field, text))
            break
        for m in re.finditer(r"\\\)([A-Za-z0-9])", text):
            out.append(_finding(item, "Space after LaTeX", SEV_LOW,
                                "Every \\(...\\) block needs a space after it, except before punctuation.",
                                field, text))
            break

    for body, msg in katex_errors(snippets).items():
        field, text = owner.get(body, (None, None))
        out.append(_finding(item, "LaTeX compiles", SEV_HIGH,
                            f"KaTeX cannot render this: {msg.splitlines()[0][:120]}", field, text))

    # KaTeX isn't installed everywhere, so also check command names against
    # the set this pipeline actually uses. An unrecognized command renders as
    # a red error in the browser, which a reviewer reading the XML won't see.
    if not katex_available():
        for body in snippets:
            field, text = owner.get(body, (None, None))
            for cmd in set(re.findall(r"\\([a-zA-Z]+)", body)):
                if cmd not in KNOWN_LATEX_COMMANDS:
                    out.append(_finding(
                        item, "Unrecognized LaTeX command", SEV_HIGH,
                        f"\\{cmd} is not a command this pipeline uses; if KaTeX does not know it, "
                        f"it renders as a red error for students. Verify it or replace it.",
                        field, text))
    return out


def check_choices(q: dict) -> list:
    """Duplicates, ordering, and the answer-visible-in-the-stem trap."""
    out = []
    item = q["id"]
    choices = q.get("choices", [])
    if len(choices) < 2:
        return out
    correct = (q.get("correct") or "").strip()

    # duplicate / equivalent choices
    seen_text, seen_val = {}, {}
    for c in choices:
        t = strip_latex(c.get("text", ""))
        if t in seen_text:
            out.append(_finding(item, "No duplicate choices", SEV_HIGH,
                                f"Choices {seen_text[t]} and {c['label']} are identical.",
                                f"choice.{c['label']}", c.get("text", "")))
        seen_text[t] = c["label"]
        v = choice_value(c.get("text", ""))
        if v is not None:
            if v in seen_val:
                out.append(_finding(item, "No equivalent choices", SEV_HIGH,
                                    f"Choices {seen_val[v]} and {c['label']} both equal {_fmt(v)}.",
                                    f"choice.{c['label']}", c.get("text", "")))
            seen_val[v] = c["label"]

    # the Question 2 bug: correct answer's value is printed in the stem
    stem = q.get("stem", "")
    if stem and correct:
        cc = next((c for c in choices if c["label"] == correct), None)
        if cc is not None:
            cv = choice_value(cc.get("text", ""))
            if cv is not None and cv in _numbers_in(stem):
                out.append(_finding(
                    item, "Answer not visible in the stem", SEV_HIGH,
                    f"The correct answer ({_fmt(cv)}) is printed in the stem, so a student can copy "
                    f"a visible number and be right without reasoning. Change the stem values so the "
                    f"answer does not appear.", "stem", stem))

    # Ordering. Two orderings are both correct by house style — smallest to
    # largest by value, or shortest to longest by character count — and which
    # one reads better is an authoring judgement. An expression set like
    # "9 + 6 / 20 + 14 / 38 + 5 / 43 + 10" is value-ordered but not
    # length-ordered, and that is a deliberate, valid choice. So this only
    # fires when NEITHER ordering holds, and it reports both targets rather
    # than asserting one is the answer.
    vals = [choice_value(c.get("text", "")) for c in choices]
    lens = [len(strip_latex(c.get("text", ""))) for c in choices]
    by_value = all(v is not None for v in vals) and vals == sorted(vals)
    by_length = lens == sorted(lens)

    if not (by_value or by_length):
        parts = []
        if all(v is not None for v in vals):
            order_v = [c["label"] for _, c in sorted(zip(vals, choices), key=lambda p: p[0])]
            parts.append(f"by value: {', '.join(order_v)}")
        order_l = [c["label"] for _, c in sorted(zip(lens, choices), key=lambda p: p[0])]
        parts.append(f"by character count: {', '.join(order_l)}")
        out.append(_finding(
            item, "Choice order", SEV_LOW,
            "These choices are ordered neither smallest-to-largest by value nor "
            "shortest-to-longest by character count. Either is acceptable — "
            + "; ".join(parts) + ". Logical grouping is also fine if that's deliberate."))
    return out


def check_math(q: dict) -> list:
    """Arithmetic the app can verify on its own: equation truth values, and
    'which is equal to X' matching."""
    out = []
    item = q["id"]
    choices = q.get("choices", [])
    correct = (q.get("correct") or "").strip()
    prompt_plain = strip_latex(q.get("prompt", "")).lower()

    # equation-truth items: exactly one choice may be a true statement
    eqs = {c["label"]: equation_sides(c.get("text", "")) for c in choices}
    parsed = {k: v for k, v in eqs.items() if v is not None}
    if len(parsed) >= 2 and ("true" in prompt_plain or "equal" in prompt_plain):
        true_labels = [k for k, (l, r) in parsed.items() if abs(l - r) < 1e-9]
        if len(parsed) == len(choices):
            if len(true_labels) == 0:
                out.append(_finding(item, "Exactly one true statement", SEV_HIGH,
                                    "No answer choice is a true equation, so the item has no correct answer."))
            elif len(true_labels) > 1:
                out.append(_finding(item, "Exactly one true statement", SEV_HIGH,
                                    f"Choices {', '.join(true_labels)} are all true equations; "
                                    f"only one choice may be true."))
            elif correct and true_labels[0] != correct:
                out.append(_finding(item, "Key matches the arithmetic", SEV_HIGH,
                                    f"Choice {true_labels[0]} is the true equation, but the key is {correct}.",
                                    "correct", correct, true_labels[0]))

    # "which expression is equal to <target>" items
    m = re.search(r"equal to\s+([0-9\s\+\-\*/\(\)]+?)\s*[\?\.]?$", strip_latex(q.get("prompt", "")))
    if m:
        target = safe_eval(m.group(1))
        if target is not None:
            matches = [c["label"] for c in choices
                       if (cv := choice_value(c.get("text", ""))) is not None and abs(cv - target) < 1e-9]
            if len(matches) > 1:
                out.append(_finding(item, "One choice equals the target", SEV_HIGH,
                                    f"Choices {', '.join(matches)} all equal {_fmt(target)}."))
            elif len(matches) == 1 and correct and matches[0] != correct:
                out.append(_finding(item, "Key matches the arithmetic", SEV_HIGH,
                                    f"Choice {matches[0]} equals {_fmt(target)}, but the key is {correct}.",
                                    "correct", correct, matches[0]))
            elif not matches:
                out.append(_finding(item, "One choice equals the target", SEV_HIGH,
                                    f"No answer choice equals {_fmt(target)}."))

    # stem equation with a blank: check the key satisfies it
    stem_plain = strip_latex(q.get("stem", ""))
    if "___" in stem_plain and stem_plain.count("=") == 1 and correct:
        cc = next((c for c in choices if c["label"] == correct), None)
        cv = choice_value(cc.get("text", "")) if cc else None
        if cv is not None:
            left, right = stem_plain.split("=")
            filled = (left.replace("___", f"({_fmt(cv)})"), right.replace("___", f"({_fmt(cv)})"))
            lv, rv = safe_eval(filled[0]), safe_eval(filled[1])
            if lv is not None and rv is not None and abs(lv - rv) > 1e-9:
                out.append(_finding(item, "Key satisfies the stem equation", SEV_HIGH,
                                    f"Substituting the key ({_fmt(cv)}) gives {_fmt(lv)} = {_fmt(rv)}, "
                                    f"which is false."))
    return out


def check_across_items(questions: list) -> list:
    """A choice value that is wrong in two or more items and never right
    anywhere is a pattern a test-wise student can exploit."""
    out = []
    as_distractor, as_correct = {}, set()
    for q in questions:
        correct = (q.get("correct") or "").strip()
        for c in q.get("choices", []):
            v = choice_value(c.get("text", ""))
            if v is None:
                continue
            if c["label"] == correct:
                as_correct.add(v)
            else:
                as_distractor.setdefault(v, []).append(q["id"])
    for v, items in sorted(as_distractor.items()):
        if len(set(items)) >= 2 and v not in as_correct:
            out.append(_finding(
                ", ".join(sorted(set(items))), "Repeated distractor across items", SEV_MED,
                f"The value {_fmt(v)} is a wrong answer in items {', '.join(sorted(set(items)))} and is "
                f"never correct in any item, which is a pattern students can learn to eliminate without "
                f"doing the math."))
    return out


# ── entry point ───────────────────────────────────────────────────────────────
def validate(lesson: dict, questions: list) -> list:
    """Every local finding for a parsed exit ticket, highest severity first.

    When an item is structurally broken — wrong number of choices, missing
    rationales, a key that names no choice — only the structural findings are
    reported for that item. Every other check reads those same fields, so it
    would produce a cascade of misleading style complaints that bury the one
    problem worth fixing. Fix the structure, save, and the rest re-runs."""
    findings = []
    for q in questions:
        structural = check_structure(q)
        if structural:
            findings += structural
            continue
        findings += check_rationales(q)
        findings += check_latex(q)
        findings += check_choices(q)
        findings += check_math(q)

    sound = [q for q in questions if not check_structure(q)]
    findings += check_across_items(sound)

    rank = {SEV_HIGH: 0, SEV_MED: 1, SEV_LOW: 2}
    findings.sort(key=lambda f: (rank.get(f["severity"], 3), str(f["item"]), f["check"]))

    # de-duplicate identical ids (same check firing twice on one field)
    seen, unique = set(), []
    for f in findings:
        if f["id"] in seen:
            continue
        seen.add(f["id"])
        unique.append(f)
    return unique


def summarize(findings: list) -> dict:
    return {
        "total": len(findings),
        SEV_HIGH: sum(1 for f in findings if f["severity"] == SEV_HIGH),
        SEV_MED: sum(1 for f in findings if f["severity"] == SEV_MED),
        SEV_LOW: sum(1 for f in findings if f["severity"] == SEV_LOW),
    }


# ── structural gate for generated XML ─────────────────────────────────────────
def assert_items_wellformed(xml_text: str, phase: str) -> None:
    """Raise ValueError unless every question in `xml_text` is structurally
    complete. Called by the generation phases right after they extract their
    XML, so a malformed item set fails at the phase that produced it and can
    simply be retried.

    Without this gate the pipeline accepted any XML that merely parsed, so a
    run that dropped an answer choice or omitted the rationales flowed all the
    way through to a rendered lesson, and a person had to notice. A model does
    occasionally produce a short item; the fix is to catch it here rather than
    to hope it doesn't.

    Deliberately checks structure only — never content. Whether the item is
    any *good* is the reviews' job.
    """
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError as e:
        raise ValueError(f"{phase}: the item XML does not parse — {e}") from e

    questions = root.findall("QUESTION")
    if not questions:
        raise ValueError(f"{phase}: no <QUESTION> elements in the output.")

    problems = []
    for q in questions:
        qid = q.get("id", "?")
        choices = q.findall("CHOICES/CHOICE")
        labels = [c.get("label") for c in choices]
        rationales = q.findall("RATIONALES/RATIONALE")
        rat_labels = [r.get("label") for r in rationales]
        correct = (q.findtext("CORRECT") or "").strip()
        prompt = (q.findtext("PROMPT") or "").strip()

        if len(choices) != 4:
            problems.append(f"item {qid}: {len(choices)} answer choices, expected 4")
        if len(set(labels)) != len(labels):
            problems.append(f"item {qid}: duplicate choice labels {labels}")
        if len(rationales) != len(choices):
            problems.append(
                f"item {qid}: {len(rationales)} rationales for {len(choices)} choices")
        missing = [l for l in labels if l not in rat_labels]
        if missing:
            problems.append(f"item {qid}: no rationale for choice(s) {', '.join(missing)}")
        if not correct:
            problems.append(f"item {qid}: <CORRECT> is empty")
        elif correct not in labels:
            problems.append(f"item {qid}: <CORRECT> is '{correct}', not one of {labels}")
        if not prompt:
            problems.append(f"item {qid}: <PROMPT> is empty")
        for r in rationales:
            if not (r.text or "").strip():
                problems.append(f"item {qid}: rationale {r.get('label')} is empty")

    if problems:
        raise ValueError(
            f"{phase}: the generated items are incomplete — "
            + "; ".join(problems)
            + ". Retry this phase."
        )
