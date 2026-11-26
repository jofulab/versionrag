# Validation codebook — answer/reference matching

The rule annotators apply, fixed before annotating so the decision is reproducible
and independent of the system being scored.

## What is being measured

Whether the **LLM judge** is reliable. The judge was given one task: decide, 0/1,
whether a generated answer matches the reference answer. So the human applies
**the same criterion** — not a better or stricter one.

This matters. If the human applies a different standard, "judge error" measures
disagreement about the task rather than judge unreliability, and the rate is
uninterpretable. Every rule below is therefore a rule about *matching the
reference*, never about answer quality, style, or truth in the world.

Reference answers are separately human-verified, so they are treated as ground
truth here.

## Unit of decision: the target fact

The **target fact** is what the question asks for — a version number, a name, a
behaviour, a cause, a yes/no. It is usually a subset of the reference answer,
because references often add elaboration nobody asked for.

Judge the target fact. Not the rest of the reference.

## Procedure

1. Read the question. State to yourself what fact would answer it.
2. Locate that fact in the reference.
3. Ask: **does the answer assert that same fact?** Enter `1` or `0`.

## Rules

**`1` — match, when the answer asserts the target fact.** Regardless of:

- paraphrase, wording, formatting, markup, units (`17` vs *"the oldest is **v17**"*)
- extra correct detail beyond the reference
- extra elaboration, examples, or reasoning
- being far longer than the reference (34 of the 142 rows are >4× longer)

**`0` — no match, when the answer:**

- states a different or contradictory value for the target fact
- gets the right entity but the wrong specifics (right feature, wrong version)
- omits the target fact, even if everything it does say is correct
- declines or hedges without committing, while the reference asserts a fact
  (*"there is no explicit evidence in the provided data…"* → `0`)

**Blank — abstain**, only when the *reference* is unusable: internally
inconsistent, unanswerable as posed, or contradicted by the source. Add a note.
Abstentions are excluded from the rate, so a high count is itself a finding.

Do **not** abstain because the call is hard. Abstain only when the reference is
the problem.

## The two cases that decide most disagreements

### Multi-claim references — the load-bearing rule

Roughly a fifth of references contain two or more claims. **The answer must
supply the target fact only.** Additional claims present in the reference but not
asked for by the question are *not* required.

> **Q:** In which Python version did evaluating `NotImplemented` in a boolean context start raising an error?
> **Reference:** *Evaluating NotImplemented in a boolean context started raising a TypeError in Python version 3.14.*
> **Target fact:** 3.14 (and that it raises).
> An answer giving 3.14 and TypeError is a match even if it omits the reference's
> phrasing or surrounding detail.

Why this rule and not "cover every claim": the judge was asked to match short
targets, so requiring full coverage would measure a stricter standard than the
judge was given and inflate the apparent error rate. In the 168 verdicts already
made, human–judge agreement is **92% on single-claim references but 62% on
multi-claim ones** — that gap is definitional, not a judge defect, and this rule
is what closes it.

### References that decline

When the reference is *"No information available."*, the correct answer is one
that **also declines**. An answer saying the context is insufficient is a **match**
(`1`), not a failure.

> **Reference:** *No information available.*
> **Answer:** *The provided context does not contain enough information to answer this question.* → `1`

8 of the 142 rows are of this shape; 12 of the 168 already annotated were, and all
were marked `1`, so this codifies existing practice rather than changing it.

## What annotators must not see

The judge's verdict, the NLI verdict, and which system produced the answer.
`to_annotate.csv` contains only id, question, reference, answer. Cell and system
live in `key/audit_key.csv`.

## Reliability check

A single annotator's rate has no measurable reliability, so:

1. A second annotator independently codes **40 rows** sampled across all cells,
   using this codebook and blind to the first annotator's verdicts.
2. Report **Cohen's κ**. κ ≥ 0.8 supports treating the primary annotations as
   reliable; below that, the disagreements indicate the codebook is
   under-specified and need adjudication before the rates are used.
3. Adjudicate every disagreement by discussion, record the resolution, and if a
   rule had to be added, re-check the rows it affects.

At n = 40 the κ estimate is coarse (SE ≈ 0.1). It is there to detect gross
divergence in how the rule is applied, not to measure agreement precisely.

## Consistency with annotations already made

168 verdicts predate this codebook. Both rules above match how they were
actually applied, so they stand. Before the rates are reported, re-check the
**37 multi-claim rows** among them against the target-fact rule — that is where a
silent standard shift would show up.
