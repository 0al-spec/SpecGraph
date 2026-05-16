# Swift Typed Tooling Lane Source Draft

## Operator Intent

SpecGraph should be able to use Swift as a pragmatic second implementation
language for typed tooling, without rewriting the Python supervisor or making
Swift a new authority layer for canonical graph mutation.

The intended first use case is read-only artifact tooling:

- typed readers for `artifact_manifest.json`, `specs/*`, and `runs/*`;
- local and HTTP-backed artifact inspection;
- validator and SDK experiments for SpecSpace and future native clients;
- Agent Passport and protocol tooling when those contracts mature.

## Working Assumptions

- Python remains the source-of-truth implementation language for supervisor
  orchestration during bootstrap.
- Swift may be useful as a typed product/runtime tooling layer because it is
  ergonomic for JSON/YAML models, CLI tools, SDKs, and Apple-native clients.
- Rust remains more appropriate if SpecGraph later needs hard low-level
  sandbox or enforcement components.
- The first Swift slice should not mutate canonical specs, proposal registries,
  or supervisor state.

## Candidate Boundary

```text
SpecGraph Python supervisor
  -> publishes neutral JSON/YAML/Markdown artifacts
  -> Swift typed tooling reads and validates those artifacts
  -> Swift tooling reports gaps or typed inspection output
  -> Python/SpecGraph governance remains canonical authority
```

## First Slice Shape

The first bounded component could be named `SpecGraphKit` or similar:

```text
tools/swift/SpecGraphKit
  read artifact_manifest.json
  read graph_dashboard.json
  read graph_backlog_projection.json
  read selected spec surfaces
  validate minimal typed contracts
  expose CLI: inspect <artifact-root-or-url>
```

This is intentionally a read-only prototype. It should prove fixture parity and
CI viability before any broader Swift adoption.
