# Native YAML formatting after lint

GitView reported on 22 November 2026 that native lint found canonical formatting
issues in Activity specifications, but the launcher offered no formatter route.
The agent invoked the installed snapshot's `tools/spec_yaml_format.py`
directly and then linted 71 nodes successfully.

The local source is
`gitview/20261122T205235Z-note-native-runtime-reports-formatting-without-a-formatter-route.md`
with SHA-256 `b73b648fd54cb077f476add7f579e992584a8c4f12d9fdbfc72f991d6b44917a`.
The operator asked to try a native formatter and noted that GitView had advanced.
The pilot therefore captures a current Activity specification with its source
revision and byte hash before using an isolated copy.
