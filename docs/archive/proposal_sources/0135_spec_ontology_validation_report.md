# Spec Ontology Validation Report Source Draft

After the legacy binding index exists, SpecGraph needs a first formal
validation surface over those bindings. This should still be report-only for
existing specs, because the ontology layer arrived after the canonical corpus.

The report should check typed structural facts instead of asking an LLM whether
the spec text "matches" the ontology. The first checks should cover required
Spec binding, relation existence, relation domain/range compatibility, and
unknown legacy terminology gaps.

Generated artifacts can be declared as `review_required` in the validation mode
contract, but hard write gating remains a later proposal.

