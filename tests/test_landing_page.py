from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_landing_page_links_to_specgraph_space():
    html = (REPO_ROOT / "landing" / "index.html").read_text(encoding="utf-8")

    assert html.count('href="https://specgraph.space"') >= 2
    assert "Open SpecGraph Space" in html
