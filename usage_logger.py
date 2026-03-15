import sqlite3
from datetime import datetime

# Kostenmodell (gpt-4.1 grob)
PROMPT_PRICE = 0.03 / 1000
COMPLETION_PRICE = 0.06 / 1000


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