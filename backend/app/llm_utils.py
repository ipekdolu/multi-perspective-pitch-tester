"""Small shared helper for structured-output LLM calls."""

from __future__ import annotations

from pydantic import ValidationError


def invoke_structured(llm, messages, max_retries: int = 2):
    """Invoke a `.with_structured_output(...)`-bound LLM, retrying on a
    malformed response.

    Seen in practice: a long-transcript synthesis call occasionally
    returned a stray text fragment (a leaked partial tool-call-like
    string) in place of a valid list field, raising a pydantic
    ValidationError. This is an occasional generation glitch on large
    structured outputs, not a systemic prompt bug — worth a retry
    rather than crashing the whole eval run over one bad sample.
    """
    last_error: ValidationError | None = None
    for _ in range(max_retries + 1):
        try:
            return llm.invoke(messages)
        except ValidationError as e:
            last_error = e
    raise last_error
