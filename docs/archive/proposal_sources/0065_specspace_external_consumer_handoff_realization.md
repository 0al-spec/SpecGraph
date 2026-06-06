# Source Draft: SpecSpace External Consumer Handoff Realization

Operator request:

> зафиксируем этот draft plan уже как todo и начнем работу по нему

Implementation constraints captured by the promoted proposal:

- do not edit deprecated `tasks.md`;
- create proposal `0065` through `make proposal-id`;
- extend the existing `external_consumer_handoff_packets` plane rather than
  creating a parallel handoff artifact;
- keep SpecGraph supervisor-centric as gap finder and contract producer;
- treat SpecSpace as an external consumer that implements UI/runtime behavior
  and returns evidence;
- add report-only evidence contract shape, without cross-repository ingestion in
  this slice;
- avoid Platform/deploy changes and SpecSpace UI implementation in this PR;
- target the first practical SpecSpace handoff at 0056/0059
  agent/executor/passport visibility, but keep it blocked until the producer
  artifact contract is stable.

