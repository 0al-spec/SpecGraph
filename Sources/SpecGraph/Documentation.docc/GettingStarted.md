# Getting Started

Use SpecGraph to keep specification work tied to explicit artifacts and runtime
evidence.

## Operator Surface

The repository keeps the following surfaces separate:

- `docs/` contains source documentation, proposal records, and operator notes.
- `tools/` contains Python tooling for derived surfaces and validation gates.
- `runs/` contains local runtime artifacts and is not published directly.
- GitHub Pages publishes the technical entrypoint and DocC documentation.
- The specgraph.tech static host publishes product-facing landing content and
  generated public artifacts.

## Routine Validation

Common local checks are exposed through Make targets:

```bash
make publish-bundle
make proposal-tracking-gate
make test
```

Use narrower tests when changing a focused workflow or documentation surface.
