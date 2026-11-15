# Independent review handoff for product drafts

The GitView Today pilot exercised independent review of one behavior spanning
multiple draft nodes. The input revision was
`404e3fda1c6e9125a6a5c6781cf0ae747a2b1ef1`. The findings and GitView's
stage-specific authoring instructions were recorded in `0a7757b`. The reviewer
read the draft and its dependencies at the input revision. Five findings went
back to the author with concrete cases for focused review after the repair.

The author and reviewer coordinated through Git revisions, a review note and
the operator's chat. SpecGraph's [candidate check](../../proposals/0235_product_draft_candidate_check.md)
provided per-file identity evidence. The pilot needed three additional pieces
of information to pick up work across that boundary:

1. The review purpose and a manifest binding the draft, relevant reference
   material and intent to one review scope.
2. Findings with stable IDs and locators, the author's disposition for each
   finding and a reference to the revised material.
3. A focused independent follow-up that evaluates the disposition on the
   repaired revision, with a record of which findings it resolved.

### Observed behavior

During repair, the installed SpecGraph runtime at `3593bd75` checked the
working copy of `docs/drafts/GITVIEW-SPEC-0110.yaml`. The report said
`checked` with `yaml_mapping`, `spec_kind` and `file_id_match`, and offered
`review_candidate`. Its source SHA-256 was
`c3615522d1985dee30126a4cdb6efa92ae98457108f3d19c8375d5f269efa732`.
The file at the original reviewed revision had SHA-256
`b66a1f63f4184e2e49e3b525418d75d6a4e3a995cfbd653683a9d0fb77311d4c`.
The differing digests identify distinct inputs. The candidate check behaved
according to its one-file contract. Binding the result to the review scope
and deciding which findings needed a follow-up remained an operator task.

The author returned revision `302d4185def0e7fdd0934e52dc54e67d8f879833`
with eight revised YAML files and proposed dispositions for the five
findings. The operator reran the installed candidate check for all eight and
matched the report digests to the committed blobs. All eight returned
`checked` and `review_candidate`. File `0110` at the repaired revision had
SHA-256 `d451fe48952449c4dad849cbd4b6b50329a6173e2d9dfbb97dbff3cc88071679`.
The author's review note carried the cross-node comparison for the PR
closure case and the other counterexamples. The eight candidate reports
provided the structural evidence for the repaired files.

The original reviewer repeated the five checks against the repaired revision.
The original lifecycle-filter and Project membership cases, GraphQL field
errors, and PR closure evidence were resolved within the checked scope. Two
findings remained partly open:

- `0110.contract.predicates` still required a local half-open interval.
  Its scenario `fixed_interval_after_device_day_change` keeps the captured
  interval fixed when the device day changes.
- The route example still obtained an exact merged count from complete Today
  membership at T1. Exactness also requires coverage of the statuses needed
  to place eligible PRs in the merged category.

The reviewer also noted that any active filter in the route example needs
its own supported outcome. The candidate status was identical for each
structurally checked file, including `0110` with its remaining interval
inconsistency. The author and reviewer used the review note and the retained
follow-up to track these outcomes across revisions.

### Reproduction for a future handoff

Review a draft against a dependency and record a finding with a counterexample.
Change the dependency first, then prepare an author response on the repaired
draft. Verify which review inputs changed, which finding the response addresses,
and which revision the independent follow-up evaluated. A successful candidate
check for a changed file supplies that file's structural evidence. A review
handoff needs enough context to show which findings remain open or require
revalidation. The pilot observation is open under RFC 0235.
