# Source Draft: Agent Passport Report-Only Verification

Operator request:

> Да, очень хочется попробовать agent passport cli на практике, приступай к
> 0071

Implementation constraints captured by the promoted proposal:

- use the actual Agent Passport CLI in report-only mode;
- keep `0070` passport references as the source of graph-agent identity;
- add safe repository-relative passport documents and mapping metadata;
- generate a sanitized verification report;
- remove `verification_not_attempted` when CLI validation succeeds;
- keep runtime enforcement, trust-store signature verification, lifecycle
  verification, and integrity-file verification out of scope;
- avoid raw passport material, local absolute paths, raw validator logs, secrets,
  or private keys in generated artifacts.

