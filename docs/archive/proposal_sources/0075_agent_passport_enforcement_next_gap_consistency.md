# Source Draft: Agent Passport Enforcement Next-Gap Consistency

Operator request:

> Хорошо. Делаем "0075 Agent Passport Enforcement Next-Gap Consistency"

Implementation intent:

- keep `agent_surface_index` useful before verification;
- align the full `make agent-passports` output after verification runs;
- prevent stale `run_report_only_passport_verification` guidance after the
  report-only verification report has succeeded;
- preserve honest runtime posture gaps without claiming enforcement.

