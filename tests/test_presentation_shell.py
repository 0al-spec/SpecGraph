from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PRESENTATION_DIR = REPO_ROOT / "landing" / "presentation" / "specgraph-sib"


def test_presentation_shell_is_static_slide_deck():
    html = (PRESENTATION_DIR / "index.html").read_text(encoding="utf-8")
    css = (PRESENTATION_DIR / "styles.css").read_text(encoding="utf-8")
    js = (PRESENTATION_DIR / "slides.js").read_text(encoding="utf-8")

    assert html.count("data-slide") == 6
    assert 'id="prevSlide"' in html
    assert 'id="nextSlide"' in html
    assert "aspect-ratio: 16 / 9" in css
    assert "@keyframes" not in css
    assert "transition" not in css
    assert 'addEventListener("keydown"' in js


def test_presentation_shell_uses_specgraph_landing_visual_tokens():
    css = (PRESENTATION_DIR / "styles.css").read_text(encoding="utf-8")

    assert "--paper: #f3f1ec" in css
    assert "--ink: #0b0b0c" in css
    assert "--signal: oklch(74% .14 240)" in css
    assert "Instrument Serif" in css
    assert "JetBrains Mono" in css
