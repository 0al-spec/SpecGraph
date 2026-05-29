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

## Boundary

Do not deploy `landing/` to GitHub Pages root. That can hide the technical
documentation entrypoint behind product navigation and create loops where
documentation links return to a landing page.
