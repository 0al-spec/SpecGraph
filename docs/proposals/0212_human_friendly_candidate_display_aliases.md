# 0212 Human-Friendly Candidate Display Aliases

## Status

Implemented bounded presentation-contract slice.

## Summary

Long generated candidate node ids and constraint statements are necessary for
stable machine references but are difficult to scan in operator-facing product
surfaces. Candidate graph consumers must not independently shorten ids because
that would create inconsistent and potentially ambiguous labels.

## Decision

`candidate_spec_graph.nodes[]` now carries a presentation-only
`display_alias` and `display_alias_source`:

- `id` remains the only canonical node identity for graph edges, repair refs,
  materialization, promotion paths, and Git operations;
- aliases are deterministic, public-safe, bounded, and disambiguated inside a
  candidate graph;
- aliases prefer a supplied public-safe alias, otherwise derive from the
  public node title;
- aliases are propagated into `candidate_overview` and candidate
  materialization outputs without replacing canonical refs.

`candidate_overview` exposes a complete `candidate_nodes.alias_by_node_id`
presentation index and topology endpoint aliases. Materialized review YAML uses
the alias as its short title while preserving the source title and canonical
candidate node id in `specification`.

## Authority and Privacy Boundary

This proposal does not:

- change canonical ids, edge refs, materialized ids, filenames, or promotion
  paths;
- add aliases as graph lookup keys or acceptance inputs;
- mutate canonical specs, write Ontology packages, accept ontology terms, or
  execute Platform or Git Service;
- expose raw idea text, private paths, secrets, or operator notes.

## Acceptance Criteria

- Candidate graphs emit stable public-safe aliases for ready nodes.
- Alias collisions resolve deterministically without changing canonical ids.
- Invalid explicit aliases block graph readiness rather than leaking private or
  multiline input.
- Candidate overview and topology retain canonical refs while exposing aliases.
- Materialized review files retain canonical ids and paths while carrying the
  short alias and original source title.
- Older artifacts without aliases remain readable by downstream consumers.

Proposal `0213` supersedes only the materialized-id/path preservation statement
in this proposal. Canonical candidate node ids and graph refs remain unchanged;
review YAML ids, filenames, dependencies, and promotion paths now include a
candidate-scoped namespace to prevent cross-product collisions.
