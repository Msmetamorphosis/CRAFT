"""
classifier.py - Task type detection for CRAFT
Classifies a user prompt into one of five enterprise task types.
"""

import json
import anthropic
from config import MODEL_DEFAULT, MAX_TOKENS, TASK_TYPES, TASK_DESCRIPTIONS


CLASSIFY_SYSTEM = """You are an expert in prompt engineering and enterprise AI use cases.
Your job is to classify a user prompt into exactly one of five task types.
You must return ONLY valid JSON with no text outside it."""

CLASSIFY_TEMPLATE = """Classify this prompt into exactly one task type.

PROMPT TO CLASSIFY:
{prompt}

TASK TYPES:
- extraction: Pulling structured data from unstructured text, documents, or reports
- reasoning: Analyzing situations, applying rules, evaluating options, explaining decisions  
- generation: Drafting emails, documents, policies, job descriptions, or other content
- ideation: Brainstorming ideas, exploring solutions, generating creative options
- conversational: Asking questions, seeking guidance, explaining situations, policy coaching

Return ONLY this JSON:
{{
  "task_type": "<one of: extraction, reasoning, generation, ideation, conversational>",
  "confidence": <number 0-100>,
  "reasoning": "<one sentence explaining why>",
  "secondary_type": "<second most likely type or null>",
  "secondary_confidence": <number 0-100 or null>
}}"""


def classify_prompt(
    client: anthropic.Anthropic,
    prompt: str,
    model: str = MODEL_DEFAULT
) -> dict:
    """
    Classify a prompt into a task type.
    Returns classification dict with task_type, confidence, reasoning.
    """
    msg = client.messages.create(
        model=model,
        max_tokens=500,
        system=CLASSIFY_SYSTEM,
        messages=[{
            "role": "user",
            "content": CLASSIFY_TEMPLATE.format(prompt=prompt[:2000])
        }]
    )

    text = msg.content[0].text.strip()
    # Strip markdown fences if present
    import re
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    try:
        result = json.loads(text)
        if result.get("task_type") not in TASK_TYPES:
            result["task_type"] = "conversational"
        return result
    except json.JSONDecodeError:
        return {
            "task_type": "conversational",
            "confidence": 50,
            "reasoning": "Could not classify with confidence, defaulting to conversational.",
            "secondary_type": None,
            "secondary_confidence": None
        }
