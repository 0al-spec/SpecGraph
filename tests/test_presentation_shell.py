from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PRESENTATION_DIR = REPO_ROOT / "landing" / "presentation" / "specgraph-sib"


def test_presentation_shell_is_static_slide_deck():
    html = (PRESENTATION_DIR / "index.html").read_text(encoding="utf-8")
    ru_html = (PRESENTATION_DIR / "index_ru.html").read_text(encoding="utf-8")
    css = (PRESENTATION_DIR / "styles.css").read_text(encoding="utf-8")
    js = (PRESENTATION_DIR / "slides.js").read_text(encoding="utf-8")

    assert html.count("data-slide") == 12
    assert 'id="prevSlide"' in html
    assert 'id="nextSlide"' in html
    assert 'viewBox="0 0 1091 1091"' in html
    assert 'class="edge ' not in html
    assert "Use arrow keys" not in html
    assert "01 / 12" in html
    assert "Measure the pipeline, not the person." in html
    assert "Intent becomes capability through gates." in html
    assert "Five quantities live on the pipeline." in html
    assert "SIB is a telescope, not a scoreboard." in html
    assert "Coverage is not semantic proof." in html
    assert "These are hypotheses, not laws." in html
    assert "SpecGraph demo" in html
    assert "False progress has mass." in html
    assert "Intent Yield" in html
    assert "Probabilistic Friction Index" in html
    assert "Agent Session Passport" in html
    assert html.count('class="speaker-notes"') == 12
    assert "speaker-notes" in (PRESENTATION_DIR / "README.md").read_text(encoding="utf-8")
    assert "aspect-ratio: 16 / 9" in css
    assert "@keyframes" not in css
    assert "transition" not in css
    assert 'addEventListener("keydown"' in js
    assert "${formatIndex(activeIndex)} / ${formatTotal(slides.length)}" in js
    assert ".demo-bridge .artifact-field span" in css
    assert ru_html.count("data-slide") == 12
    assert ru_html.count('class="speaker-notes"') == 12
    assert '<html lang="ru">' in ru_html
    assert 'class="deck-ru"' in ru_html
    assert "Артефакты стали дешёвыми." in ru_html
    assert "Измеряйте производственный контур." in ru_html
    assert "Пять величин живут на пайплайне." in ru_html
    assert "SIB — телескоп, а не KPI." in ru_html
    assert "Покрытие строк не доказывает намерение." in ru_html
    assert "демо SpecGraph" in ru_html
    assert "Нельзя прятать «неизвестно»" in ru_html
    assert '<script src="slides.js"></script>' in ru_html
    assert "fonts/glanz/Glanz.otf" in css
    assert "fonts/glanz/Glanz Italic.otf" in css
    assert 'font-family: "Glanz"' in css
    assert ".deck-ru .anchor-row span" in css
    assert "overflow-wrap: anywhere" in css
    assert (PRESENTATION_DIR / "fonts" / "glanz" / "Glanz.otf").is_file()
    assert (PRESENTATION_DIR / "fonts" / "glanz" / "Glanz Italic.otf").is_file()
    assert "Free for Personal and Commercial Use" in (
        PRESENTATION_DIR / "fonts" / "glanz" / "Glanz License.txt"
    ).read_text(encoding="utf-8")


def test_presentation_shell_uses_specgraph_landing_visual_tokens():
    css = (PRESENTATION_DIR / "styles.css").read_text(encoding="utf-8")

    assert "--paper: #f3f1ec" in css
    assert "--ink: #0b0b0c" in css
    assert "--signal: oklch(74% .14 240)" in css
    assert "Instrument Serif" in css
    assert "JetBrains Mono" in css
