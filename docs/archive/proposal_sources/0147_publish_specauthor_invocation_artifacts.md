# Source: Publish SpecAuthor Invocation Artifacts

Operator intent: make the new SpecAuthor invocation chain visible to downstream
consumers after the prompt-side authoring flow exists.

The slice publishes only public-safe, derived `runs/` artifacts:

- the typed invocation artifact;
- its contract report;
- the compact authoring-flow report.

Raw prompts, raw model outputs, generated draft prose, local paths, canonical
spec mutations, ontology package writes, and owner-decision imports remain out
of scope.
