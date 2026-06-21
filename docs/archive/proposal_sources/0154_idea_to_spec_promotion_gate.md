# Source: Idea-to-Spec Promotion Gate

Operator intent: after candidate materialization exists, add one final
review-only gate before handing the candidate to Platform.

The gate should aggregate pre-SIB/coherence, repair loop, and materialization
artifacts. It should allow promotion only when the repair preview is ready,
owner/operator context requirements are resolved, materialization is ready, and
promotion paths are safe and non-empty.

It must not execute prompt agents, mutate specs, write Ontology packages, create
branches or commits, open pull requests, publish read models, merge, or accept
candidate specs.
