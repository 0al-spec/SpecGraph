# SpecGraph / SIB Metrics Vision Deck

Static 16:9 HTML deck for explaining why AI-native software development should
measure the feature pipeline, not only human activity or artifact output.

Open `index.html` directly in a browser. The deck intentionally avoids build
tooling, slide transitions, autoplay, and animation so the artifact can double
as a landing-style page and a presentation surface.

## Narrative Shape

- Act I: AI makes artifacts cheap; intent preservation becomes the core
  measurement problem.
- Act II: SIB, pre-SIB, Yield, Cost, Drift, and Confidence describe pipeline
  integrity.
- Act III: SpecGraph is the graph of intent, work, evidence, runtime signals,
  and feedback where those metrics live.
- Act IV: the prototype starts as an event log and becomes a self-improving
  observe / diagnose / intervene / measure loop.

## Editing Notes

- Keep each slide short: one main claim, one visual, and a small amount of
  supporting text.
- Keep `speaker-notes` as the longer narrative layer for a 15-20 minute talk;
  visible slide text should remain sparse.
- Use diagrams for relationships between `SpecGraph`, `SpecSpace`, `Metrics`,
  and the AI-driven SDLC loop.
- Preserve the warm editorial style from the SpecGraph landing page: serif
  display type, strict rules, monochrome surfaces, and a single blue signal
  accent.
- Prefer semantic HTML sections with `data-slide` for future content changes.
