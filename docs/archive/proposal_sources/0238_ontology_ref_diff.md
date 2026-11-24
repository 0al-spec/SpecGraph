# Review ontology declarations during specification promotion

GitView reported that explicit terminology and ontology references disappeared
when a draft was transferred to a canonical specification. A term inventory of
the successor then had zero entries. The report correctly reflected its input,
but the author had to compare the draft and the successor to find the omission.

The local observation is
`gitview/20261116T134700Z-review-note-agent-omitted-ontology-bindings-on-promotion.md`
(SHA-256 `c2106fa2d39ccb84ea60b3c5a8984b2be66cc6bece4aabae1d103393b1626bed`).
GitView revision `6d725ef` contains the affected root pair in
`docs/drafts/GITVIEW-SPEC-0001.yaml` and `specs/nodes/GITVIEW-SPEC-0001.yaml`.
The operator requested a two-file diff of the declarations with source
locations and an optional explanation for an intentional removal.

The pilot compared the two files at that revision and reported 14 removed
declarations. Thirteen are terminology keys and one is a qualified reference.
