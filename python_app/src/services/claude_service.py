CLAUDE_PROMPT = """You are an options mentor. Summarize this pick for a newer investor (≤120 words).
Explain why it's attractive, key risks, and when to re-evaluate. Use plain English.
DATA:
{pick_json}
"""

def summarize_pick_with_claude(pick: dict) -> str:
    # TODO: call Anthropic API
    return "Placeholder summary."
