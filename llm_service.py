import os
import anthropic

# =========================================================
# Konfiguration
# =========================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not set")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# =========================================================
# LLM Service
# =========================================================

def generate_response(messages, system_prompt, enable_web_search=True, max_tokens=800):
    """
    Zentrale LLM-Funktion.

    Parameters:
        messages: List[dict]  (Chat-Format, role "user"/"assistant" – kein "system" hier,
                   die Anthropic-API erwartet den System-Prompt separat)
        system_prompt: str
        enable_web_search: bool
        max_tokens: int

    Returns:
        dict:
            {
                "text": str,
                "usage": {
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int
                }
            }
    """

    kwargs = {
        "model": MODEL_NAME,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": messages,
    }

    if enable_web_search:
        kwargs["tools"] = [{"type": "web_search_20260209", "name": "web_search"}]

    response = client.messages.create(**kwargs)

    # Text extrahieren
    output_text = ""
    for block in response.content:
        if block.type == "text":
            output_text += block.text

    usage = response.usage
    prompt_tokens = usage.input_tokens if usage else 0
    completion_tokens = usage.output_tokens if usage else 0

    return {
        "text": output_text,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }
