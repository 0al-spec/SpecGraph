# 0209 Depth Repair Effect Visibility

Source draft for proposal `0209`.

Structural-depth repair became actionable in proposals `0207` and `0208`, but
downstream product surfaces still need durable evidence of what changed after a
rerun. Add a review-only `structural_depth_delta` to rerun preview and
materialization artifacts:

- before/after candidate structure counts;
- added event-storming entry refs;
- added workflow relation evidence;
- remaining shallow dimensions;
- compact status: `resolved`, `improved`, `still_shallow`, `unchanged`, or
  `not_measured`.

The delta is visibility only. It must not change Metrics schemas, add a score,
become a gate, mutate canonical specs or intake sources, write Ontology
packages, accept ontology terms, execute prompt agents, create Git artifacts, or
publish read models.
