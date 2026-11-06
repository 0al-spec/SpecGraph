# Source draft: composable verification workflow

Captured in the current SpecGraph conversation on 2026-11-06. Excerpts are
agent-attributed conversation evidence; speaker identity and original message
timestamps are not independently attested.

## Human intent

After the agent reported a fresh ExamCalc execution and criterion report:

> Да, и важно чтобы обойти прогон было формально сложно

The user then described the desired interaction:

> Хорошо бы уметь составлять некие workflow из функций супервизора и других возможностей графа, чтобы например такие проверки не были сложными ритуалами

## Proposed bounded interpretation

The assistant proposed one profile `verify-criteria/v1`: pin inputs, execute
tests, bind observations, collect/validate, present the result in Supervisor.
Existing 0224/0226 contracts are reused; 0225 admission remains separate.
Required execution cannot be replaced by merely supplying an old report.
The first slice excludes a universal workflow engine and automatic retries.

This paragraph is assistant synthesis, not a verbatim human requirement or an
assertion that the profile already exists. Three read-only agent investigations
checked Supervisor seams, contract boundaries and the ExamCalc pilot.

## Authorization and limits

The user requested delegation: «Отдай задачу сабагентам», then asked to check
the results: «Проверь». After the assistant proposed recording the consolidated
contract, the user said:

> Хорошо оформляй пропозал. Если надо будет что-то исправить, проверить - запускай сабагента и не жди их ответов. Я потом тебя сам позову.

This authorizes proposal preparation and asynchronous checking/fixing within
that task. It is not approval to activate the future runtime profile, change
canonical specifications, assign `tests_verified` or publish trusted receipts.

## Existing evidence and return path

The ExamCalc pilot was executed at local commit
`775e0100006d98ed9ad6054e70954c54df934b39`; reports were retained at local commit
`9e0cd21`. The working baseline for SpecGraph is
`002eb0691b39ea2ccdcc50d0c5c31fc84022e3bf`. These identify prior source
observations, not new workflow execution or hosted evidence.

Return through SG-RFC-0234 and `proposal::0234-verification-workflow`.
