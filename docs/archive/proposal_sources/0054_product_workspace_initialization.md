# Product Workspace Initialization Source Draft

## Source Context

Product workspace governance and stable-mode enforcement now define how
SpecGraph should behave once a project workspace exists. The remaining operator
friction is the entrypoint: a user should not need to hand-create every
directory, config file, and first artifact before SpecGraph can safely work on
an external product.

The new `Platform` repository also introduces a shared control-plane layer for
workspace catalogs and service topology. SpecGraph should own the product
workspace initialization contract, while Platform may orchestrate it.

## Operator Intent

Provide a clear first action for creating a new product workspace:

- generate a valid `specgraph.project.yaml`;
- create the minimal folder-document layout;
- default to `product_workspace` governance;
- optionally capture a root intent or source note;
- publish an initialization report that SpecSpace and Platform can inspect;
- never import or mutate SpecGraph core specs as part of product setup.

## Desired Outcome

Create a proposal for a bounded Product Workspace Initialization capability.
The proposal should define the contract before implementation:

- command or API shape;
- generated files and directories;
- initialization report artifact;
- interaction with Platform workspace catalog;
- SpecSpace preview/status expectations;
- SpecPM private-registry import boundary;
- safety rules for no auto-import and no core mutation.

## Boundary

This proposal is not a full platform installer. It does not implement hosted
accounts, cloud provisioning, SpecSpace project switching, or SpecPM package
materialization. It defines the SpecGraph-owned initialization boundary that
those services can call or display.
