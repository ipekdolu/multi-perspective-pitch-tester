"""Server-side audit trail for challenge outcomes.

Deliberately separate from LangGraph's `challenge_log` state field: this
is the MCP server's own record, independent of any particular graph run
or checkpoint. JSONL: append-only, one record per line, trivially
inspectable without a DB client.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent / "challenge_audit.jsonl"


def append_entry(persona_id: str, challenge: str, outcome: str) -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "persona_id": persona_id,
        "challenge": challenge,
        "outcome": outcome,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
