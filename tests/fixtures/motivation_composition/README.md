# Motivation composition fixture

The two dependency YAML files are exact source bytes from Ontology 0.5.0,
commit `0fcc94469d971aaf39fcc182bc5c6b8acff37fd2`.
`origins.json` pins each source URL and SHA-256; `LICENSE` retains the MIT license.
The events file is from the explicit `versions/0.2.0` directory, not the
unversioned 0.1.0 package.

`project.yaml` is synthetic and has no accepted GitView terms. Its relation
references the existing `motivcore:Motive`. The shared package draft statuses
are preserved.

Integration tests compile fresh IR with the caller-selected compiler.
No generated IR or machine-local executable is checked in.
