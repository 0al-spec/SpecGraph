"""Shared idea-to-spec contract constants used by standalone tools."""

from __future__ import annotations

INTAKE_SESSION_CANDIDATE_SOURCE_INPUT_CONTRACT_REF = (
    "specgraph.idea-to-spec.intake-session-candidate-source-input.v0.1"
)

SESSION_PRIVACY_RAW_IDEA_TEXT_PUBLISHED_KEY = "raw_idea_text_published_in_session"
PUBLISHED_PAYLOAD_PRIVACY_RAW_IDEA_TEXT_PUBLISHED_KEY = "raw_idea_text_published"

PUBLIC_SAFE_PRIVACY_KEYS = (
    "raw_idea_text_published",
    "raw_prompt_published",
    "raw_model_output_published",
    "raw_operator_note_published",
)
