# SIB / SpecGraph 10-Minute Deck

Static 16:9 HTML deck for a 10-minute SIB Metrics talk followed by a
10-minute SpecGraph demo. The deck explains why AI-native software development
should measure the capability pipeline instead of only human activity or
artifact output.

Open `index.html` directly in a browser. The deck intentionally avoids build
tooling, slide transitions, autoplay, and animation so the artifact can double
as a landing-style page and a presentation surface.

Use `index_ru.html` for the Russian-language visible slide copy. It shares the
same static CSS/JS shell, keeps the same 12-slide structure, and uses the local
Glanz font files in `fonts/glanz/` for Cyrillic display headings.

Use `index_ru_v2.html` for the alternate 10-slide Russian variant. It carries
the SpecGraph speaker narrative — AI makes artifacts cheap, so measure meaning,
not volume:

1. Дешёвые артефакты — AI made artifacts cheap; count is no longer a signal.
2. Output ≠ ценность — more output does not mean more value.
3. SIB — сигнал баланса — SIB is the descriptive Spec/Impl balance, not a score.
4. Стоимость capability — cost per internally accepted capability.
5. pre-SIB — readiness of the path before launching an agent.
6. Yield — where the pipeline leaks meaning (intents → accepted).
7. Drift — broken code vs. a semantic shift of intent.
8. Доказательство смысла — evidence must prove intent, plus confidence/unknown.
9. Метрики на переходах — the capability pipeline and per-transition metrics.
10. Слои и тезис — observables/control/outcomes, measure the pipeline not people.

It reuses `styles.css`, `slides.js`, and the Glanz fonts, and layers a few extra
diagram components (SIB fraction, boxed statements, two-branch decision tree,
transition table, and the layered stack) in `styles_v2.css`. The longer
speaker-script narration lives in each slide's `speaker-notes`.

## Narrative Shape

- Slides 1-2: AI makes artifacts cheap; measure the pipeline, not the person.
- Slides 3-4: the capability pipeline and five observables: SIB, Yield, Cost,
  Drift, and pre-SIB.
- Slides 5-6: SIB is a decomposable diagnostic signal; evidence must prove
  intent instead of only executing lines.
- Slides 7-8: validation hypotheses and the handoff into the SpecGraph demo.
- Backup slides: False Progress Mass, IY/FC/ICC, PFI/CSI, and Agent Session
  Passport for Q&A.

## Editing Notes

- Keep each slide short: one main claim, one visual, and a small amount of
  supporting text.
- Keep `speaker-notes` as the longer Russian-speaking narrative layer for the
  10-minute talk; visible slide text should remain sparse.
- Use diagrams for intent fan-out, the capability pipeline, semantic evidence,
  and backup metric explanations.
- Preserve the warm editorial style from the SpecGraph landing page: serif
  display type, strict rules, monochrome surfaces, and a single blue signal
  accent.
- Prefer semantic HTML sections with `data-slide` for future content changes.
