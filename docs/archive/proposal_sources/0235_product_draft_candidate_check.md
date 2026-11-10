# Check a product draft in place

On 2026-11-10 the GitView pilot reported that `next-move --target-spec`
could not select a specification in `docs/drafts/`. The installed SpecGraph
revision was `8303a681d8f2b33989b004de6954dc371c86da51`. The command
looked for the target in `specs/nodes/` as designed. The workaround copied
the draft into a disposable workspace, so the operator had to check that
the copy still matched the source.

The local 0AL entry is
`gitview/20261110T060637Z-note-draft-target-unavailable-to-next-move.md`
(SHA-256 `16690c337fcde3753e0d31ba0911614d16a499fb88010585aeabe52383e846c1`).
It classifies this as workflow friction and suggests explicit read-only
candidate selection or documenting the isolated workspace procedure.

The operator approved proceeding through the full SpecGraph process after
reviewing the proposed check by path, with a report bound to the draft's
SHA-256 and identified as candidate evidence.
