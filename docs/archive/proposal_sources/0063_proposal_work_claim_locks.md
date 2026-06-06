# Source Draft: Proposal Work Claim Locks

Operator question:

> А у нас есть механизм валидации того факта, что proposal уже взят в работу и
> по идее залочен?

Decision captured by the promoted proposal:

- add a repository-tracked proposal work claim registry;
- validate active claims for required fields, expiry, and duplicate
  `(proposal_id, scope)` ownership;
- add a deterministic read-only proposal ID allocator that inspects docs,
  source drafts, registries, and active claims before returning the next ID;
- keep the mechanism as coordination and review visibility, not as a distributed
  lock or permission system;
- do not require every proposal PR to have a claim until the workflow proves
  useful.
