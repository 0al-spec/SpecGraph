"""Read-only HTML presentation of the collector's criterion report payload.

This module formats the report produced by criterion_observation_report;
it neither ingests arbitrary reports nor recomputes evidence decisions.
"""

import json
from collections import Counter
from html import escape


def literal(value: object) -> str:
    return escape(str(value), quote=True)


def json_block(value: object) -> str:
    return (
        "<pre>"
        + literal(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        + "</pre>"
    )


def details(title: str, value: object) -> str:
    return f"<details><summary>{literal(title)}</summary>{json_block(value)}</details>"


def findings_html(findings: list[dict]) -> str:
    if not findings:
        return "<p>No diagnostic findings recorded.</p>"
    return (
        "<ul>"
        + "".join(
            f"<li><strong>{literal(f['kind'])}</strong> · <code>{literal(f['code'])}</code>"
            f"<p>{literal(f['detail'])}</p></li>"
            for f in findings
        )
        + "</ul>"
    )


def measurements_html(steps: list[dict]) -> str:
    if not steps:
        return "<p>No expected measurements declared.</p>"
    rows = []
    for step in steps:
        measured = step.get("observed_measurement")
        observation = "<p>Not observed</p>" if measured is None else json_block(measured)
        label = step.get("step_text") or "Step text unavailable"
        rows.append(
            "<tr><th scope='row'>"
            f"<p>{literal(label)}</p><small>"
            f"Producer result: {literal(step.get('producer_status') or 'unavailable')}</small>"
            "</th><td><span class='measurement-label'>Expected</span>"
            f"{json_block(step['expected_measurement'])}</td>"
            f"<td><span class='measurement-label'>Observed</span>{observation}</td></tr>"
        )
    return (
        "<div class='table-scroll'><table><caption>Selected measurements</caption>"
        "<thead><tr><th scope='col'>Step</th><th scope='col'>Expected</th>"
        "<th scope='col'>Observed</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def criterion_html(row: dict, position: int) -> str:
    source, observation = row["source"], row["observation"]
    parts = [
        f"<section class='criterion' id='criterion-{position}'>",
        f"<p class='eyebrow'>Criterion {position + 1} · {literal(source['pointer'])}</p>",
        f"<h2>{literal(source['text'])}</h2>",
        "<dl class='statuses'>",
        f"<div><dt>Binding integrity</dt><dd>{literal(row['binding_integrity'])}</dd></div>",
        f"<div><dt>Observed outcome</dt><dd>{literal(row['observed_outcome'])}</dd></div>",
        f"<div><dt>Trust admission</dt><dd>{literal(row['admission'])}</dd></div></dl>",
    ]
    if observation is not None:
        parts += [
            measurements_html(observation["steps"]),
            "<p>Run success: <code>"
            + literal(json.dumps(observation["run_success"]))
            + "</code> · Case finished: <code>"
            + literal(json.dumps(observation["case_finished"]))
            + "</code></p>",
            "<p>Only selected measured steps are shown above; this is not the full scenario.</p>",
            details("All case step results", observation["case_step_statuses"]),
        ]
    else:
        parts.append("<p>No joined observation is available for this criterion.</p>")
        for binding in row["bindings"]:
            parts.append(f"<h3>Expected by binding {literal(binding['passport_binding_id'])}</h3>")
            parts.append(measurements_html(binding["assertions"]))
        if not row["bindings"]:
            parts.append("<p>No test binding is declared.</p>")
    parts += [
        "<h3>Gaps and diagnostics</h3>",
        findings_html(row["findings"]),
        details(
            "Criterion source and exact evidence identities",
            {
                "source": source,
                "bindings": row["bindings"],
                "journal": row["journal"],
                "observation": observation,
            },
        ),
        "</section>",
    ]
    return "\n".join(parts)


STYLE = """
:root {color-scheme:light; font:16px/1.55 system-ui,sans-serif; color:#182b33; background:#eef3f4}
body {margin:0} main {max-width:1080px; margin:auto; padding:28px 20px 60px}
header,.criterion,.overview {background:white; border:1px solid #c6d5d9;
 border-radius:12px; padding:24px; margin-bottom:20px}
h1 {font-size:2rem; margin:.3rem 0} h2 {font-size:1.3rem; line-height:1.4}
h3 {font-size:1.05rem} .eyebrow,small {color:#455c66} .eyebrow {margin:0}
dl.statuses {display:flex; flex-wrap:wrap; gap:12px}
.statuses div {background:#eef3f4; padding:10px 14px; border-radius:6px}
dt {font-size:.85rem} dd {margin:0; font-weight:650}
table {width:100%; border-collapse:collapse; text-align:left}
th,td {padding:12px; border:1px solid #c6d5d9; vertical-align:top}
thead,caption {background:#eef3f4} caption {text-align:left; padding:10px; font-weight:650}
.table-scroll {overflow-x:auto} pre {white-space:pre-wrap; overflow-wrap:anywhere;
 margin:0; font-size:.85rem; line-height:1.5} p,small,h2,code {overflow-wrap:anywhere}
details {margin-top:16px} summary {cursor:pointer; font-weight:600}
details pre {padding:14px; margin-top:8px; background:#f3f6f7}
a {color:#075a81} a:focus-visible,summary:focus-visible {outline:3px solid #146d93}
.notice {border-left:4px solid #b86c00; padding-left:12px}
.measurement-label {display:none}
@media(max-width:600px) {main {padding:12px} header,.criterion,.overview {padding:16px}
 h1 {font-size:1.6rem} table,caption,tbody,tr,th,td {display:block}
 thead {position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%)}
 tr {margin-bottom:14px} td,th {min-width:0}
 .measurement-label {display:block; font-weight:650; margin-bottom:8px}}
@media print {body {background:white} main {max-width:none} details {break-inside:avoid}}
"""


def render_html(report: dict) -> str:
    """Format the freshly collected payload without adding or upgrading outcomes."""
    inventory, rows = report["inventory"], report["criteria"]
    counts = Counter(row["observed_outcome"] for row in rows)
    inventory_text = (
        f"Complete inventory · {inventory['criterion_count']} criteria"
        if inventory["complete"]
        else "Incomplete inventory · total criterion count unknown"
    )
    scope = report["evidence_scope"]
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; "
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">",
        "<title>Criterion observations</title>",
        f"<style>{STYLE}</style></head><body><main>",
        "<header><p class='eyebrow'>SpecGraph · Local test observations</p>",
        "<h1>What the retained tests show</h1>",
        f"<p>{literal(' · '.join(scope['spec_ids']))}</p>",
        f"<p>{literal(inventory_text)}</p>",
        "<p class='notice'>Binding integrity, observed outcome and trust admission are separate. "
        "A passed observation does not establish trusted runtime verification.</p>",
        f"<p>Source-build provenance: <code>{literal(report['execution_source_provenance'])}</code>"
        f" · Admission: <code>{literal(report['admission'])}</code>"
        f" · Receipt: <code>{literal(json.dumps(report['receipt']))}</code></p></header>",
        "<section class='overview'><h2>Criterion inventory</h2>",
        "<p>Observed outcomes in the displayed rows: "
        + literal(
            ", ".join(f"{status}: {count}" for status, count in sorted(counts.items())) or "none"
        )
        + ".</p><ol>",
    ]
    parts += [
        f"<li><a href='#criterion-{i}'>{literal(row['source']['text'])}</a> — "
        f"{literal(row['binding_integrity'])} / {literal(row['observed_outcome'])}</li>"
        for i, row in enumerate(rows)
    ]
    parts += ["</ol><h3>Collection gaps and diagnostics</h3>", findings_html(report["findings"])]
    if report["unmatched_bindings"]:
        parts += [
            "<p class='notice'>Some bindings do not identify a criterion in this inventory.</p>",
            details("Unmatched bindings", report["unmatched_bindings"]),
        ]
    parts.append("</section>")
    parts += [criterion_html(row, i) for i, row in enumerate(rows)]
    provenance = {key: value for key, value in report.items() if key != "criteria"}
    parts += [
        "<section class='overview'><h2>Sources and reproducibility</h2>",
        "<p>Source locators are shown exactly as collected; no repository URL is inferred.</p>",
        f"<p>JSON report SHA-256: <code>{literal(report['content_sha256'])}</code></p>",
        details("Selected inputs, lifecycle, provider and hashes", provenance),
        "</section></main></body></html>",
    ]
    return "\n".join(parts)
