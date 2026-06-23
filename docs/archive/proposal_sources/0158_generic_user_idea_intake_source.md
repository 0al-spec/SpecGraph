# 0158 Generic User Idea Intake Source

## Source Draft

The product idea-to-spec flow needs a generic input for a new user idea so a
future workspace can replace Team Decision Log without adding product-specific
scripts, Make targets, or system-level names.

The first bounded slice should accept a structured `user_idea_intake_source`
JSON artifact and emit an existing `idea_event_storming_seed` artifact. The
existing event-storming intake builder should remain the next step. This keeps
the chain small and avoids adding prompt-agent execution or candidate graph
generation before the intake contract is stable.

The source should include product workspace identity, root intent,
ontology/domain/context hints, ontology layer/model applicability defaults, and
optional event-storming hints. It should filter raw prompt/model/operator trace
fields from event-storming hints and leave raw intent publication policy to the
existing intake builder, which already digests raw intent text.

The slice must remain review-only: no canonical spec mutation, no Ontology
package writes, no Git Service calls, no branches, no pull requests, and no
SpecSpace mutation UI.
