# RFC 0223 native preparation: independent Astra audit

## Reviewed snapshot and verdict

- Request: independent audit on GPT 6 Astra / Max.
- PR: [#757](https://github.com/0al-spec/SpecGraph/pull/757).
- Head: `13ed5d072d44a08eaf3bb9fe4c487ec4b159e5a7`.
- Base: `9283e69f25a4a7cd0e3cef8dbbb32f15561f204f`.
- Verdict: **needs changes**, one P2 and two P3; no P1.
- Mode: read-only detached snapshot. No edits, builds, full suites, Supervisor,
  additional models or GitHub mutations.

This verdict applies to the reviewed head. Author corrections below are separate
evidence and do not constitute independent approval of a later candidate.

## Findings and author corrections

### P2: missing timestamp compatibility

The [baseline](https://github.com/0al-spec/SpecGraph/blob/13ed5d072d44a08eaf3bb9fe4c487ec4b159e5a7/docs/reviews/0223_native_bdd_supervisor_candidate.yaml#L100)
and new ID/step checks omit the consumer's recursive `normalize_yaml_scalars`
before validation. YAML date/datetime in IDs, titles, steps and references become
ISO strings. Datetime text can change its separator to `T`; a timestamp ID can
collide with a quoted ISO string.

Risk: a shared loader could pass the original 71 cases and still alter legacy
acceptance or silently transfer coercion into strict validation.

Author correction: four characterization cases cover date/datetime across BDD
fields and references, plus normalized ID collisions. The baseline now describes
the transformation. Strict v1 checks original decoded types before coercion;
the compatibility path retains existing normalization.

### P3: aggregation and prerequisite skips unspecified

Fixed policy order alone does not decide whether `{id: A, steps: [], extra: true}`
returns one error or both errors, or whether Values is skipped. Different
implementations could produce different findings and traces under the same text.

Author correction: eligible policies accumulate findings; skips require explicit
prerequisite reasons. Policy, source-index and field ordering are defined.
Unknown fields/invalid steps do not suppress eligible ID checks. A future combined
case requires `unsupported_field`, then `invalid_value`, with both policies
unsatisfied. No Python combinator or strict runtime is implemented here.

### P3: historical diagnostic completeness overstated

The [evidence assessment](https://github.com/0al-spec/SpecGraph/blob/13ed5d072d44a08eaf3bb9fe4c487ec4b159e5a7/docs/reviews/0223_native_bdd_preparation_evidence.json#L52)
claims all historical matches are quotes, while the packet preserves only an
eight-line excerpt. The classifier truncates `evidence` to three matches.
Two repetitions of the excerpt followed by a real diagnostic can have the same
classifier projection as the repetitions alone.

Author correction: distinguish a **reproduced false-positive trigger** from the
author's historical observation. Full historical completeness is not established
by the curated packet. The main agent reproduced the excerpt-only trigger and
truncated-projection counterexample directly from the classifier function's AST,
without starting Supervisor. The historical gate remains pending.

## Independent checks at the reviewed head

- Focused tests: **71 passed** (50 new + 21 existing), cache and bytecode writes
  disabled, temporary workspaces used.
- Preparation pins: input, raw/curated candidate, excerpt, corpus, consumer,
  both test files and historical proposal matched.
- Pinned corpus: 69 canonical SpecGraph files without scenario containers and
  six Zeusus files with 100 scenarios (`10/26/12/14/14/24`); IDs unique and exact
  field set `id/scenario/steps`. Four historical observation packet digests matched.
- Current-consumer preview: eleven local references, blocked only on
  `review_pending`/`outlined`, evidence not evaluated, mutations denied.
- Parent scope, temporary ID, privacy, FeaturePassport boundary and absence of
  implementation/adoption claims checked.
- DocC sync, registry contents/markers, Markdown links and diff checks passed.
  Proposal tracking via Supervisor was not run by the auditor.

## Author follow-up evidence

The updated preparation has **75 compatibility cases** (54 + 21), five criteria
and thirteen future native BDD cases. The two added future cases concern timestamp
type boundaries and combined errors; these future cases are not executed runtime
evidence. Raw/input files and corpus/observation pins stay historical. Curated and
test hashes plus preview counts are refreshed separately in
[preparation evidence](0223_native_bdd_preparation_evidence.json).

Canonical adoption, shared-loader implementation, profile activation, normalized
digests, Gherkin exchange, source migration and trusted admission remain deferred.
