# External Ontology Import Plane

Working draft for proposal 0060.

SpecGraph needs a lower semantic integration boundary for the sibling
`Ontology` repository without treating external ontology packages, compiler
outputs, or prompt-agent drafts as direct canonical graph mutations.

The motivating operator concerns are:

- Ontology is beginning to own reusable domain ontology packages,
  `ontologyc`, prompt contracts, and Hypercode IR imports.
- SpecGraph is already mature and must not be rewritten around a new bottom
  layer.
- SpecGraph changes are accepted through proposal flow, not direct mutation.
- Prompt execution should eventually run as isolated agent invocations with
  Agent Passport constraints, bounded model policy, and typed outputs.
- Ontology packages need a storage and lock model comparable in care to the
  SpecPM handoff/import work.
- Ontology now has golden intent semantic expectations, a repeatability harness,
  and a governance protocol; SpecGraph imports must preserve references to that
  evidence instead of treating package digests alone as sufficient approval.

The desired first step is a bridge proposal, not runtime implementation. It
should define:

- external ontology package references;
- concept references;
- semantic bindings between SpecGraph subjects and ontology concepts;
- import locks with source, version, and digest;
- ontology gaps and ontology-import proposals;
- prompt-pack references and prompt-agent invocation boundaries;
- adjacency to SpecPM, Agent Passport, prompt overlay, executor adapter, and
  Platform packaging work.

The proposal should explicitly forbid:

- direct canonical writes from `ontologyc`;
- direct canonical writes from prompt agents;
- copying the whole Ontology package contract into SpecGraph;
- replacing SpecGraph's existing ontology/governance model;
- implementing registry, Docker packaging, SpecAgent runtime, or SpecSpace UI
  in this first slice.

Successful adoption should make later work sequenced and reviewable:

1. external ontology import plane;
2. `ontologyc` adapter/report contract;
3. ontology governance evidence and decision-record references;
4. prompt-agent invocation contract;
5. Agent Passport capability profiles for prompt agents;
6. Platform package/cache/deploy materialization;
7. SpecSpace review surface for ontology proposals.
