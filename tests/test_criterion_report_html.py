"""Presentation preserves collector decisions, missing evidence and literal input."""

import copy
from html.parser import HTMLParser

import pytest

from test_criterion_observation_provider import TEXT
from test_criterion_observation_provider import retained as retained
from traceability.criterion_report_html import render_html


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


def test_html_preserves_complete_inventory_and_measurements(retained):
    report = retained.run()
    before = copy.deepcopy(report)
    html = render_html(report)
    doc = Document(html)
    text = " ".join(doc.text)
    assert report == before
    assert html == render_html(report)
    for criterion in TEXT:
        assert criterion in text
    assert "Complete inventory · 3 criteria" in text
    assert "passed: 3" in text
    assert '"issued": true' in text and '"reissued": false' in text
    assert "Binding integrity" in text and "Observed outcome" in text
    assert "producer_declared" in text and "not_evaluated" in text
    assert report["content_sha256"] in text
    assert sum(tag == "caption" for tag, _ in doc.tags) == 3
    ids = {attrs.get("id") for _, attrs in doc.tags}
    for tag, attrs in doc.tags:
        if tag == "a":
            assert attrs["href"].startswith("#criterion-")
            assert attrs["href"][1:] in ids


def test_missing_evidence_retains_expected_measurements_and_every_criterion(retained):
    selection = retained.select()
    (retained.artifacts / "run.ndjson").unlink()
    report = retained.run(selection)
    text = " ".join(Document(render_html(report)).text)
    assert "unavailable: 3" in text
    for criterion in TEXT:
        assert criterion in text
    assert text.count("No joined observation") == 3
    assert text.count("Not observed") == 4
    assert '"count": 1' in text
    assert "binding_input" in text
    assert "retained input unavailable: run.ndjson" in text


def test_incomplete_inventory_is_not_zero_successful_criteria(retained):
    report = retained.run()
    report.update(
        criteria=[],
        findings=[{"kind": "invalid", "code": "spec_input", "detail": "Malformed source"}],
    )
    report["inventory"].update(complete=False, criterion_count=None)
    text = " ".join(Document(render_html(report)).text)
    assert "total criterion count unknown" in text
    assert "Malformed source" in text
    assert "0 criteria" not in text and "passed:" not in text


@pytest.mark.parametrize("state", ["failed", "partial", "pending", "skipped", "unavailable"])
def test_projection_never_upgrades_collector_outcome(retained, state):
    report = retained.run()
    report["criteria"][0]["observed_outcome"] = state
    report["criteria"][0]["observation"]["run_success"] = False
    html = render_html(report)
    assert f"<dd>{state}</dd>" in html
    assert f"{state}: 1" in html
    assert "Run success: <code>false</code>" in html


def test_conflicting_bindings_and_unmatched_plan_rows_remain_visible(retained):
    binding = copy.deepcopy(retained.plan["bindings"][0])
    binding["assertions"][0]["expected_measurement"] = {"count": 999}
    retained.plan["bindings"].append(binding)
    foreign = copy.deepcopy(binding)
    foreign["pointer"] = "/acceptance/99"
    retained.plan["bindings"].append(foreign)
    report = retained.run()
    text = " ".join(Document(render_html(report)).text)
    assert "conflict" in text
    assert "Expected by binding" in text
    assert '"count": 1' in text and '"count": 999' in text
    assert "Unmatched bindings" in text
    assert "/acceptance/99" in text


def test_evidence_text_cannot_inject_markup_urls_or_scripts(retained):
    report = retained.run()
    attack = '</pre><script>alert(1)</script><img src="https://example.invalid/leak">'
    report["criteria"][0]["source"]["text"] = attack
    report["criteria"][0]["observation"]["steps"][0]["step_text"] = attack
    report["criteria"][0]["observation"]["steps"][0]["observed_measurement"] = {attack: attack}
    report["findings"] = [{"kind": "invalid", "code": attack, "detail": attack}]
    report["evidence_scope"]["repository_id"] = attack
    doc = Document(render_html(report))
    assert attack in " ".join(doc.text)
    assert not {"script", "img", "iframe", "object", "link", "form"} & {tag for tag, _ in doc.tags}
    assert not any(
        "src" in attrs or any(k.startswith("on") for k in attrs) for _, attrs in doc.tags
    )
    assert any(attrs.get("http-equiv") == "Content-Security-Policy" for _, attrs in doc.tags)


def test_unbound_criterion_is_not_dropped(retained):
    retained.plan["bindings"] = retained.plan["bindings"][1:]
    text = " ".join(Document(render_html(retained.run())).text)
    assert TEXT[0] in text and "No test binding is declared." in text
    assert "unbound / unavailable" in text
