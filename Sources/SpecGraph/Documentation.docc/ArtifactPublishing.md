# Artifact Publishing

SpecGraph publishes technical and product-facing surfaces through separate
channels.

## GitHub Pages

GitHub Pages owns the technical surface:

- the repository root technical entrypoint;
- DocC documentation under `documentation/specgraph/`;
- a mixed-case `documentation/SpecGraph/` compatibility redirect for old links;
- future generated technical artifacts that belong next to documentation.

The root page is intentionally not the product landing page.

## Static Host

The specgraph.tech static host owns product-facing landing content and generated
public artifact bundles. Static-host uploads must remain non-destructive so
separate jobs do not delete each other's files.

`make publish-bundle` is the canonical build command for the public artifact
bundle. It refreshes product-facing surfaces before packaging `specs/` and
`runs/`, including the Agent Passport producer artifacts consumed by SpecSpace:
executor adapter index, agent surface index, known passport index, verification
report, verification gap index, runtime evidence index, and runtime evidence
detail artifacts.

The bundle manifest and safety gate must fail closed when required public
surfaces are missing, so a successful static-host deploy means HTTP consumers
can discover the same product-facing surfaces through `artifact_manifest.json`
that local operators see in `runs/`.

## Boundary

Do not deploy `landing/` to GitHub Pages root. That can hide the technical
documentation entrypoint behind product navigation and create loops where
documentation links return to a landing page.
