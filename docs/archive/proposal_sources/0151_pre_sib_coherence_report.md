# Source: Pre-SIB Coherence Report

Operator intent: after candidate graph generation, add a compact metric and
coherence report that gives the user and future repair loop measurable control
before any canonical graph write.

This first pre-SIB slice should stay deterministic and review-only. It computes
basic structural, ontology coverage, acceptance-criteria coverage, unresolved
gap, and unsupported-claim signals from `candidate_spec_graph`. It should not
pretend to be final SIB, run prompt agents, repair the graph, or materialize
canonical specs.
