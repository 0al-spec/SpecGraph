# 0156 CLI Candidate Approval Flow

Operator intent: define how CLI-mode SpecGraph should ask for and record a
human/operator approval when an idea-to-spec candidate is ready to advance
toward Git Service promotion.

Bounded scope:

- preserve the separation between agent recommendation, operator approval, Git
  Service execution, repository review, merge, and read-model publication;
- define a future `candidate_approval_decision` artifact;
- require explicit approval before a ready candidate can become a promotion
  request attempt;
- keep the artifact public-safe by using refs, digests, status, and findings
  instead of raw prompts, private notes, local paths, or credentials;
- keep the first slice proposal-only until runtime wiring is ready.

Out of scope:

- prompt-agent execution;
- SpecSpace mutation UI;
- canonical SpecGraph spec mutation;
- ontology package writes;
- Git branch, commit, PR, merge, or read-model publishing;
- treating a ready candidate as accepted product truth.

