import os
from openai import OpenAI

# =========================================================
# Konfiguration
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4.1")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set")

client = OpenAI(api_key=OPENAI_API_KEY)


# =========================================================
# LLM Service
# =========================================================

def generate_response(messages, enable_web_search=True, max_tokens=800):
    """
    Zentrale LLM-Funktion.
    
    Parameters:
        messages: List[dict]  (Chat-Format)
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

    tools = []
    if enable_web_search:
        tools.append({"type": "web_search"})

    response = client.responses.create(
        model=MODEL_NAME,
        input=messages,
        tools=tools if tools else None,
        max_output_tokens=max_tokens
    )

    # Text extrahieren
    output_text = ""
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    output_text += content.text

    usage = response.usage

    return {
        "text": output_text,
        "usage": {
            "prompt_tokens": usage.input_tokens if usage else 0,
            "completion_tokens": usage.output_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0
        }
    }