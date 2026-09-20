import os
import sqlite3
from datetime import datetime

# Aktuelle Anthropic-Preise (USD pro 1M Token, Stand 2026).
# An das tatsächlich über ANTHROPIC_MODEL konfigurierte Modell gekoppelt,
# statt hartcodiert auf ein einzelnes Modell (siehe TECH_ASSESSMENT.md A2.15).
PRICING_PER_MILLION_TOKENS = {
    "claude-sonnet-5": {"prompt": 2.00, "completion": 10.00},
    "claude-opus-5": {"prompt": 5.00, "completion": 25.00},
    "claude-haiku-4-5": {"prompt": 1.00, "completion": 5.00},
}

MODEL_NAME = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
_pricing = PRICING_PER_MILLION_TOKENS.get(MODEL_NAME)

if _pricing is None:
    # Unbekanntes/neues Modell in .env: Kostenschätzung fällt auf Sonnet-5-Preise
    # zurück und ist damit nicht exakt, aber es gibt keinen stillen Fehlwert mehr.
    _pricing = PRICING_PER_MILLION_TOKENS["claude-sonnet-5"]
    print(
        f"WARNUNG: Keine Preisdaten für Modell '{MODEL_NAME}' hinterlegt – "
        f"Kostenschätzung verwendet Fallback-Preise (claude-sonnet-5)."
    )

PROMPT_PRICE = _pricing["prompt"] / 1_000_000
COMPLETION_PRICE = _pricing["completion"] / 1_000_000


def log_usage(username, prompt_tokens, completion_tokens, total_tokens):

    cost = (
        prompt_tokens * PROMPT_PRICE +
        completion_tokens * COMPLETION_PRICE
    )

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO usage (
        username,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        cost_estimate,
        timestamp
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        username,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        cost,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()

    return cost
