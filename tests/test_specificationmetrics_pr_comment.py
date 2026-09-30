import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "specificationmetrics_pr_comment.py"
SPEC = importlib.util.spec_from_file_location("specificationmetrics_pr_comment", SCRIPT)
COMMENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMMENT)


def report(revision, status="complete", provisional=False):
    return {
        "schema_version": 1,
        "project": "0al-spec/SpecGraph",
        "contract_digest": "a" * 64,
        "status": status,
        "primary": {
            "source_digest": "c" * 64,
            "source_revision": revision * 40,
            "specification_definitions": 3,
            "remaining_opportunities": 639,
            "ratio": 3 / 639,
            "dead_specifications": 0,
            "unknown_specifications": 0,
            "provisional": provisional,
        },
    }


def test_rendered_comment_has_primary_and_supplementary_deltas_without_source_text():
    base, head = report("a"), report("b")
    diff = {
        "contract_digest": "a" * 64,
        "before_source_digest": "c" * 64,
        "after_source_digest": "c" * 64,
        "supplementary": {
            "python_complexity": {
                "status": "comparable",
                "delta": {"cc_sum": -2, "cc_max": -1, "cog_sum": -3, "cog_max": -2, "sloc": 1},
            },
            "duplication": {"status": "not_comparable", "delta": None},
        },
        "untrusted": "malicious PR source text",
    }
    rendered = COMMENT.render_comment(
        base, head, diff, "https://github.com/0al-spec/SpecGraph/actions/runs/12345"
    )
    assert "Specifications (S) | 3 | 3 (+0)" in rendered
    assert "Remaining opportunities (U) | 639 | 639 (+0)" in rendered
    assert "cc_sum -2" in rendered
    assert "**Clone pairs / duplicate lines / tokens:** not comparable" in rendered
    assert "malicious PR source text" not in rendered
    assert COMMENT.COMMENT_MARKER in rendered


def test_noncomplete_collections_are_labeled_and_null_ratio_is_not_infinity():
    base, head = report("a", "provisional", True), report("b", "partial", True)
    base["primary"]["ratio"] = None
    head["primary"]["remaining_opportunities"] = 0
    head["primary"]["ratio"] = None
    diff = {
        "contract_digest": "a" * 64,
        "before_source_digest": "c" * 64,
        "after_source_digest": "c" * 64,
        "supplementary": {},
    }
    rendered = COMMENT.render_comment(
        base, head, diff, "https://github.com/0al-spec/SpecGraph/actions/runs/12345"
    )
    assert "base `provisional`, head `partial`" in rendered
    assert "n/a" in rendered
    assert "not comparable; see pinned-tool diagnostics" in rendered


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b, a, d: a.update(project="attacker/repo"),
        lambda b, a, d: d.update(contract_digest="b" * 64),
        lambda b, a, d: a["primary"].update(specification_definitions=-1),
    ],
)
def test_renderer_rejects_invalid_report_identity_and_comparison(mutate):
    base, head = report("a"), report("b")
    diff = {
        "contract_digest": "a" * 64,
        "before_source_digest": "c" * 64,
        "after_source_digest": "c" * 64,
        "supplementary": {},
    }
    mutate(base, head, diff)
    with pytest.raises(ValueError):
        COMMENT.render_comment(
            base, head, diff, "https://github.com/0al-spec/SpecGraph/actions/runs/12345"
        )


def test_untrusted_revision_is_redacted_instead_of_echoed():
    base, head = report("a"), report("b")
    base["primary"]["source_revision"] = "untrusted PR title and source text"
    diff = {
        "contract_digest": "a" * 64,
        "before_source_digest": "c" * 64,
        "after_source_digest": "c" * 64,
        "supplementary": {},
    }
    rendered = COMMENT.render_comment(
        base, head, diff, "https://github.com/0al-spec/SpecGraph/actions/runs/12345"
    )
    assert "untrusted PR title and source text" not in rendered
    assert "`unavailable` → `bbbbbbbbbbbb`" in rendered
